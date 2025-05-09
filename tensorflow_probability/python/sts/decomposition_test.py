# Copyright 2018 The TensorFlow Probability Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
"""Tests for STS decomposition methods."""

import numpy as np
import tensorflow.compat.v1 as tf1
import tensorflow.compat.v2 as tf
from tensorflow_probability.python.internal import tensorshape_util
from tensorflow_probability.python.internal import test_util
from tensorflow_probability.python.sts import decomposition
from tensorflow_probability.python.sts.components import local_linear_trend
from tensorflow_probability.python.sts.components import seasonal
from tensorflow_probability.python.sts.components import sum as sum_lib
from tensorflow_probability.python.sts.forecast import forecast
from tensorflow_probability.python.sts.internal import missing_values_util


tfl = tf.linalg


JAX_MODE = False


class _DecompositionTest(test_util.TestCase):

  def _build_model_and_params(self,
                              num_timesteps,
                              param_batch_shape,
                              num_posterior_draws=10):
    seed = test_util.test_seed_stream()
    rng = test_util.test_np_rng(seed())
    observed_time_series = self._build_tensor(
        rng.randn(*(param_batch_shape + [num_timesteps])))

    # Build an STS model with multiple components
    day_of_week = seasonal.Seasonal(
        num_seasons=7,
        observed_time_series=observed_time_series,
        name='day_of_week')
    llt = local_linear_trend.LocalLinearTrend(
        observed_time_series=observed_time_series, name='local_linear_trend')
    model = sum_lib.Sum(
        components=[day_of_week, llt],
        observed_time_series=observed_time_series)

    # Sample test params from the prior (faster than posterior samples).
    param_samples = [p.prior.sample([num_posterior_draws], seed=seed())
                     for p in model.parameters]

    return model, observed_time_series, param_samples

  def testDecomposeByComponentSupportsBatchShape(self):
    num_timesteps = 12
    param_batch_shape = [2, 1]
    model, observed_time_series, param_samples = self._build_model_and_params(
        num_timesteps=num_timesteps,
        param_batch_shape=param_batch_shape)

    component_dists = decomposition.decompose_by_component(
        model,
        observed_time_series=observed_time_series,
        parameter_samples=param_samples)

    self._check_component_shapes_helper(
        model, component_dists,
        expected_shape=param_batch_shape + [num_timesteps])

  def testDecomposeByComponentSupportsMissingData(self):
    num_timesteps = 8
    model, observed_time_series, param_samples = self._build_model_and_params(
        num_timesteps=num_timesteps, param_batch_shape=[])

    # Check that missing values are properly handled by setting them to NaN,
    # and asserting (below) that the NaNs don't propagate.
    is_missing = [True, True, False, False, True, False, False, True]
    nans = np.zeros([num_timesteps], dtype=self.dtype)
    nans[is_missing] = np.nan
    masked_time_series = missing_values_util.MaskedTimeSeries(
        time_series=observed_time_series + nans, is_missing=is_missing)

    component_dists = decomposition.decompose_by_component(
        model,
        observed_time_series=masked_time_series,
        parameter_samples=param_samples)

    component_means_, component_stddevs_ = self.evaluate(
        ([d.mean() for d in component_dists.values()],
         [d.stddev() for d in component_dists.values()]))
    self.assertTrue(np.all(np.isfinite(component_means_)))
    self.assertTrue(np.all(np.isfinite(component_stddevs_)))

  def testDecomposeForecastByComponentSupportsBatchShape(self):
    num_timesteps = 12
    param_batch_shape = [2, 1]
    model, observed_time_series, param_samples = self._build_model_and_params(
        num_timesteps=num_timesteps,
        param_batch_shape=param_batch_shape)

    num_steps_forecast = 7
    forecast_dist = forecast(model, observed_time_series, param_samples,
                             num_steps_forecast)
    component_forecasts = decomposition.decompose_forecast_by_component(
        model, forecast_dist=forecast_dist, parameter_samples=param_samples)

    self._check_component_shapes_helper(
        model, component_forecasts,
        expected_shape=param_batch_shape + [num_steps_forecast])

  def _check_component_shapes_helper(self, model, component_dists,
                                     expected_shape):
    # Given a dict of component marginal distributions, check that the dict
    # has the expected structure and that the distributions have the expected
    # shape (and that shape is static if possible).
    for component in model.components:
      component_stddev = component_dists[component].stddev()
      component_shape = self._get_tensor_shape(component_stddev)
      self.assertAllEqual(component_shape, expected_shape)

  def _get_tensor_shape(self, tensor):
    if self.use_static_shape:
      # If input shapes are static, result shapes should be too.
      return tensorshape_util.as_list(tensor.shape)
    else:
      return self.evaluate(tf.shape(tensor))

  def _build_tensor(self, ndarray):
    """Convert a numpy array to a TF placeholder.

    Args:
      ndarray: any object convertible to a numpy array via `np.asarray()`.

    Returns:
      placeholder: a TensorFlow `placeholder` with default value given by the
      provided `ndarray`, dtype given by `self.dtype`, and shape specified
      statically only if `self.use_static_shape` is `True`.
    """

    ndarray = np.asarray(ndarray).astype(self.dtype)
    if JAX_MODE:
      return ndarray
    return tf1.placeholder_with_default(
        ndarray, shape=ndarray.shape if self.use_static_shape else None)


@test_util.test_all_tf_execution_regimes
class DecompositionTestStatic32(_DecompositionTest):
  dtype = np.float32
  use_static_shape = True


# Run in graph mode only to reduce test weight.
@test_util.jax_disable_test_missing_functionality('dynamic shape')
class DecompositionTestDynamic64(_DecompositionTest):
  dtype = np.float64
  use_static_shape = False

del _DecompositionTest  # Don't run tests for the base class.

if __name__ == '__main__':
  test_util.main()
