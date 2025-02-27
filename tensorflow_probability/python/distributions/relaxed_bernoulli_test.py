# Copyright 2018 The TensorFlow Probability Authors.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
"""Tests for the RelaxedBernoulli distribution."""

import numpy as np
import scipy.special
import tensorflow.compat.v1 as tf1
import tensorflow.compat.v2 as tf
from tensorflow_probability.python.distributions import relaxed_bernoulli
from tensorflow_probability.python.internal import tensorshape_util
from tensorflow_probability.python.internal import test_util


@test_util.test_all_tf_execution_regimes
class RelaxedBernoulliTest(test_util.TestCase):

  def testP(self):
    """Tests that parameter P is set correctly. Note that dist.p != dist.pdf."""
    temperature = 1.0
    p = [0.1, 0.4]
    dist = relaxed_bernoulli.RelaxedBernoulli(
        temperature, probs=p, validate_args=True)
    self.assertAllClose(p, self.evaluate(dist.probs))

  def testLogits(self):
    temperature = 2.0
    logits = [-42., 42.]
    dist = relaxed_bernoulli.RelaxedBernoulli(
        temperature, logits=logits, validate_args=True)
    self.assertAllClose(logits, self.evaluate(dist.logits))

    self.assertAllClose(scipy.special.expit(logits),
                        self.evaluate(dist.probs_parameter()))

    p = [0.01, 0.99, 0.42]
    dist = relaxed_bernoulli.RelaxedBernoulli(
        temperature, probs=p, validate_args=True)
    self.assertAllClose(scipy.special.logit(p),
                        self.evaluate(dist.logits_parameter()))

  def testInvalidP(self):
    temperature = 1.0
    invalid_ps = [1.01, 2.]
    for p in invalid_ps:
      with self.assertRaisesOpError(
          'Argument `probs` has components greater than 1.'):
        dist = relaxed_bernoulli.RelaxedBernoulli(
            temperature, probs=p, validate_args=True)
        self.evaluate(dist.probs)

    invalid_ps = [-0.01, -3.]
    for p in invalid_ps:
      with self.assertRaisesOpError(
          'Argument `probs` has components less than 0.'):
        dist = relaxed_bernoulli.RelaxedBernoulli(
            temperature, probs=p, validate_args=True)
        self.evaluate(dist.probs)

    valid_ps = [0.0, 0.5, 1.0]
    for p in valid_ps:
      dist = relaxed_bernoulli.RelaxedBernoulli(
          temperature, probs=p, validate_args=True)
      self.assertEqual(p, self.evaluate(dist.probs))

  def testShapes(self):
    for batch_shape in ([], [1], [2, 3, 4]):
      temperature = 1.0
      p = np.random.random(batch_shape).astype(np.float32)
      dist = relaxed_bernoulli.RelaxedBernoulli(
          temperature, probs=p, validate_args=True)
      self.assertAllEqual(batch_shape,
                          tensorshape_util.as_list(dist.batch_shape))
      self.assertAllEqual(batch_shape, self.evaluate(dist.batch_shape_tensor()))
      self.assertAllEqual([], tensorshape_util.as_list(dist.event_shape))
      self.assertAllEqual([], self.evaluate(dist.event_shape_tensor()))

  def testZeroTemperature(self):
    """If validate_args, raises error when temperature is 0."""
    temperature = tf.constant(0.0)
    p = tf.constant([0.1, 0.4])
    with self.assertRaisesOpError('`temperature` must be positive.'):
      dist = relaxed_bernoulli.RelaxedBernoulli(
          temperature, probs=p, validate_args=True)
      sample = dist.sample(seed=test_util.test_seed())
      self.evaluate(sample)

  def testDtype(self):
    temperature = tf.constant(1.0, dtype=tf.float32)
    p = tf.constant([0.1, 0.4], dtype=tf.float32)
    dist = relaxed_bernoulli.RelaxedBernoulli(
        temperature, probs=p, validate_args=True)
    self.assertEqual(dist.dtype, tf.float32)
    self.assertEqual(dist.dtype, dist.sample(
        5, seed=test_util.test_seed()).dtype)
    self.assertEqual(dist.probs.dtype, dist.prob([0.0]).dtype)
    self.assertEqual(dist.probs.dtype, dist.log_prob([0.0]).dtype)

    temperature = tf.constant(1.0, dtype=tf.float64)
    p = tf.constant([0.1, 0.4], dtype=tf.float64)
    dist64 = relaxed_bernoulli.RelaxedBernoulli(
        temperature, probs=p, validate_args=True)
    self.assertEqual(dist64.dtype, tf.float64)
    self.assertEqual(dist64.dtype, dist64.sample(
        5, seed=test_util.test_seed()).dtype)

  def testLogProb(self):
    t = np.array(1.0, dtype=np.float64)
    p = np.array(0.1, dtype=np.float64)  # P(x=1)
    dist = relaxed_bernoulli.RelaxedBernoulli(t, probs=p, validate_args=True)
    xs = np.array([0.1, 0.3, 0.5, 0.9], dtype=np.float64)
    # analytical density from Maddison et al. 2016
    alpha = np.array(p / (1 - p), dtype=np.float64)
    expected_log_pdf = (
        np.log(t) + np.log(alpha) + (-t - 1) * (np.log(xs) + np.log(1 - xs)) -
        2 * np.log(alpha * np.power(xs, -t) + np.power(1 - xs, -t)))
    log_pdf = self.evaluate(dist.log_prob(xs))
    self.assertAllClose(expected_log_pdf, log_pdf)

  def testBoundaryConditions(self):
    temperature = 1e-2
    dist = relaxed_bernoulli.RelaxedBernoulli(
        temperature, probs=1.0, validate_args=True)
    self.assertAllClose(-np.inf, self.evaluate(dist.log_prob(0.0)))
    self.assertAllClose(np.inf, self.evaluate(dist.log_prob(1.0)))

    dist = relaxed_bernoulli.RelaxedBernoulli(
        temperature, probs=0.0, validate_args=True)
    self.assertAllClose(np.inf, self.evaluate(dist.log_prob(0.0)))
    self.assertAllClose(-np.inf, self.evaluate(dist.log_prob(1.0)))

  def testSamplesAtBoundaryNotNaN(self):
    temperature = 1e-2
    dist = relaxed_bernoulli.RelaxedBernoulli(
        temperature, probs=1.0, validate_args=True)
    self.assertFalse(np.any(np.isnan(self.evaluate(
        dist.log_prob(dist.sample(10, seed=test_util.test_seed()))))))

    dist = relaxed_bernoulli.RelaxedBernoulli(
        temperature, probs=0.0, validate_args=True)
    self.assertFalse(np.any(np.isnan(self.evaluate(
        dist.log_prob(dist.sample(10, seed=test_util.test_seed()))))))

  def testPdfAtBoundary(self):
    dist = relaxed_bernoulli.RelaxedBernoulli(
        temperature=0.1, logits=[[3., 5.], [3., 2]], validate_args=True)
    pdf_at_boundary = self.evaluate(dist.prob([0., 1.]))
    log_pdf_at_boundary = self.evaluate(dist.log_prob([0., 1.]))
    self.assertAllPositiveInf(pdf_at_boundary)
    self.assertAllPositiveInf(log_pdf_at_boundary)

  def testAssertValidSample(self):
    temperature = 1e-2
    p = [0.2, 0.6, 0.5]
    dist = relaxed_bernoulli.RelaxedBernoulli(
        temperature, probs=p, validate_args=True)
    with self.assertRaisesOpError('Sample must be non-negative.'):
      self.evaluate(dist.log_cdf([0.3, -0.2, 0.5]))
    with self.assertRaisesOpError('Sample must be less than or equal to `1`.'):
      self.evaluate(dist.prob([0.3, 0.1, 1.2]))

  def testSampleN(self):
    """mean of quantized samples still approximates the Bernoulli mean."""
    temperature = 1e-2
    p = [0.2, 0.6, 0.5]
    dist = relaxed_bernoulli.RelaxedBernoulli(
        temperature, probs=p, validate_args=True)
    n = 10000
    samples = dist.sample(n, seed=test_util.test_seed())
    self.assertEqual(samples.dtype, tf.float32)
    sample_values = self.evaluate(samples)
    self.assertAllInRange(sample_values, 0., 1.)

    frac_ones_like = np.sum(sample_values >= 0.5, axis=0) / n
    self.assertAllClose(p, frac_ones_like, atol=1e-2)

  def testParamTensorFromLogits(self):
    x = tf.constant([-1., 0.5, 1.])
    d = relaxed_bernoulli.RelaxedBernoulli(
        temperature=1., logits=x, validate_args=True)
    self.assertAllClose(
        *self.evaluate([x, d.logits_parameter()]),
        atol=0, rtol=1e-4)
    self.assertAllClose(
        *self.evaluate([tf.math.sigmoid(x),
                        d.probs_parameter()]),
        atol=0,
        rtol=1e-4)

  def testParamTensorFromProbs(self):
    x = tf.constant([0.1, 0.5, 0.4])
    d = relaxed_bernoulli.RelaxedBernoulli(
        temperature=1., probs=x, validate_args=True)
    logit = lambda x: tf.math.log(x) - tf.math.log1p(-x)
    self.assertAllClose(
        *self.evaluate([logit(x), d.logits_parameter()]),
        atol=0, rtol=1e-4)
    self.assertAllClose(
        *self.evaluate([x, d.probs_parameter()]),
        atol=0, rtol=1e-4)

  def testUnknownShape(self):
    logits = tf.Variable(np.zeros((1, 5)), shape=tf.TensorShape((1, None)))
    d = relaxed_bernoulli.RelaxedBernoulli(0.5, logits, validate_args=True)
    self.evaluate(logits.initializer)
    d.sample(seed=test_util.test_seed())

    if not tf.executing_eagerly():
      logits = tf1.placeholder(tf.float32, shape=(1, None))
      d = relaxed_bernoulli.RelaxedBernoulli(
          0.5, logits=logits, validate_args=True)
      d.sample(seed=test_util.test_seed())

  def testCdfAgreesWithLogProb(self):
    # Shape [N, 1, 1, 1]. This is to support broadcasting and the last dimension
    # for evaluating against the quadrature nodes.

    # Choose probs in a modest range such that the density isn't extremeely
    # skewed for quadrature.
    probs = tf.random.uniform(
        minval=0.3,
        maxval=0.7,
        shape=[int(1e2)],
        dtype=np.float64,
        seed=test_util.test_seed())[..., tf.newaxis, tf.newaxis, tf.newaxis]
    temp = np.array([0.5, 1., 2.], dtype=np.float64)[
        ..., np.newaxis, np.newaxis]
    dist = relaxed_bernoulli.RelaxedBernoulli(
        temp, probs=probs, validate_args=True)

    x = np.array([0.1, 0.25, 0.5, 0.75, 0.9], dtype=np.float64)
    # Do quadrature on the probability density from 0 to x.
    nodes, weights = scipy.special.roots_legendre(500)
    rescaled_nodes = x[..., np.newaxis] / 2. * (nodes + 1.)
    expected_log_cdf = (tf.math.log(x / 2.) + tf.math.reduce_logsumexp(
        np.log(weights) + dist.log_prob(rescaled_nodes), axis=-1))[
            ..., tf.newaxis, :]
    actual_log_cdf, expected_log_cdf = self.evaluate(
        [dist.log_cdf(x), expected_log_cdf])
    self.assertAllClose(expected_log_cdf, actual_log_cdf, rtol=2e-2)

  def testCdfNotNanNearEndpoints(self):
    probs = np.linspace(0., 1., 30, dtype=np.float32)[..., None]
    temp = 1e-1
    dist = relaxed_bernoulli.RelaxedBernoulli(
        temp, probs=probs, validate_args=True)
    x = [0., 0.25, 0.5, 0.75, 1.]
    cdf = self.evaluate(dist.cdf(x))
    self.assertFalse(np.any(np.isnan(cdf)))
    # Check that the CDF is strictly increasing for probs not in {0, 1}.
    self.assertTrue(np.all(np.diff(cdf[1:-1]) >= 0.))
    self.assertAllEqual([1., 1., 1., 1., 1.], cdf[0])
    self.assertAllEqual([0., 0., 0., 0., 1.], cdf[-1])


@test_util.test_all_tf_execution_regimes
class RelaxedBernoulliFromVariableTest(test_util.TestCase):

  @test_util.tf_tape_safety_test
  def testGradientLogits(self):
    x = tf.Variable([-1., 1])
    self.evaluate(x.initializer)
    d = relaxed_bernoulli.RelaxedBernoulli(0.5, logits=x, validate_args=True)
    with tf.GradientTape() as tape:
      loss = -d.log_prob([0, 1])
    g = tape.gradient(loss, d.trainable_variables)
    self.assertLen(g, 1)
    self.assertAllNotNone(g)

  @test_util.tf_tape_safety_test
  def testGradientProbs(self):
    x = tf.Variable([0.1, 0.7])
    self.evaluate(x.initializer)
    d = relaxed_bernoulli.RelaxedBernoulli(0.5, probs=x, validate_args=True)
    with tf.GradientTape() as tape:
      loss = -d.sample(seed=test_util.test_seed())
    g = tape.gradient(loss, d.trainable_variables)
    self.assertLen(g, 1)
    self.assertAllNotNone(g)

  @test_util.tf_tape_safety_test
  def testGradientTemperature(self):
    x = tf.Variable([0.2, 2.])
    self.evaluate(x.initializer)
    d = relaxed_bernoulli.RelaxedBernoulli(
        x, probs=[0.8, 0.5], validate_args=True)
    with tf.GradientTape() as tape:
      loss = -d.sample(seed=test_util.test_seed())
    g = tape.gradient(loss, d.trainable_variables)
    self.assertLen(g, 1)
    self.assertAllNotNone(g)

  def testAssertionsProbs(self):
    x = tf.Variable([0.1, 0.7, 0.0])
    d = relaxed_bernoulli.RelaxedBernoulli(0.5, probs=x, validate_args=True)
    self.evaluate(x.initializer)
    self.evaluate(d.sample(seed=test_util.test_seed()))
    with tf.control_dependencies([x.assign([0.1, -0.7, 0.0])]):
      with self.assertRaisesOpError(
          'Argument `probs` has components less than 0.'):
        self.evaluate(d.sample(seed=test_util.test_seed()))

    with tf.control_dependencies([x.assign([0.1, 1.7, 0.0])]):
      with self.assertRaisesOpError(
          'Argument `probs` has components greater than 1.'):
        self.evaluate(d.sample(seed=test_util.test_seed()))

  def testAssertionsTemperature(self):
    x = tf.Variable(.8)
    probs = [0.1, .35, 0.7]
    d = relaxed_bernoulli.RelaxedBernoulli(x, probs=probs, validate_args=True)
    self.evaluate(x.initializer)
    self.evaluate(d.sample(seed=test_util.test_seed()))
    with tf.control_dependencies([x.assign(-1.2)]):
      with self.assertRaisesOpError(
          'Argument `temperature` must be positive.'):
        self.evaluate(d.sample(seed=test_util.test_seed()))

  def testSupportBijectorOutsideRange(self):
    probs = np.array([0.45, 0.07, 0.32, 0.99])
    temp = 1.
    dist = relaxed_bernoulli.RelaxedBernoulli(
        temp, probs=probs, validate_args=True)
    eps = 1e-6
    x = np.array([-2.3, -eps, 1. + eps, 1.4])
    bijector_inverse_x = dist.experimental_default_event_space_bijector(
        ).inverse(x)
    self.assertAllNan(self.evaluate(bijector_inverse_x))


if __name__ == '__main__':
  test_util.main()
