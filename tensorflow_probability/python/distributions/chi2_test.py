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
"""Tests for initializers."""

import numpy as np
from scipy import special
from scipy import stats
import tensorflow.compat.v2 as tf

from tensorflow_probability.python.distributions import chi2
from tensorflow_probability.python.distributions import kullback_leibler
from tensorflow_probability.python.internal import test_util


@test_util.test_all_tf_execution_regimes
class Chi2Test(test_util.TestCase):

  def testChi2LogPDF(self):
    batch_size = 6
    df = tf.constant([2.0] * batch_size, dtype=np.float64)
    df_v = 2.0
    x = np.array([2.5, 2.5, 4.0, 0.1, 1.0, 2.0], dtype=np.float64)
    dist = chi2.Chi2(df=df, validate_args=True)
    expected_log_pdf = stats.chi2.logpdf(x, df_v)

    log_pdf = dist.log_prob(x)
    self.assertEqual(log_pdf.shape, (6,))
    self.assertAllClose(self.evaluate(log_pdf), expected_log_pdf)

    pdf = dist.prob(x)
    self.assertEqual(pdf.shape, (6,))
    self.assertAllClose(self.evaluate(pdf), np.exp(expected_log_pdf))

  def testLogPdfAssertsOnInvalidSample(self):
    d = chi2.Chi2(df=13.37, validate_args=True)
    with self.assertRaisesOpError('Sample must be non-negative.'):
      self.evaluate(d.log_prob([14.2, -5.3]))

  def testPdfOnBoundary(self):
    d = chi2.Chi2(df=[2., 4., 1.], validate_args=True)
    log_prob_boundary = self.evaluate(d.log_prob(0.))
    self.assertAllFinite(log_prob_boundary[0])
    self.assertAllNegativeInf(log_prob_boundary[1])
    self.assertAllPositiveInf(log_prob_boundary[2])

    prob_boundary = self.evaluate(d.prob(0.))
    self.assertAllFinite(prob_boundary[:1])
    self.assertAllPositiveInf(prob_boundary[2])

  def testChi2CDF(self):
    batch_size = 6
    df = tf.constant([2.0] * batch_size, dtype=np.float64)
    df_v = 2.0
    x = np.array([2.5, 2.5, 4.0, 0.1, 1.0, 2.0], dtype=np.float64)

    dist = chi2.Chi2(df=df, validate_args=True)
    expected_cdf = stats.chi2.cdf(x, df_v)

    cdf = dist.cdf(x)
    self.assertEqual(cdf.shape, (6,))
    self.assertAllClose(self.evaluate(cdf), expected_cdf)

  def testChi2Quantile(self):
    batch_size = 6
    df = np.linspace(1., 20., batch_size).astype(np.float64)[..., np.newaxis]
    x = np.linspace(0., 1., 13).astype(np.float64)
    dist = chi2.Chi2(df=df, validate_args=True)
    expected_quantile = stats.chi2.ppf(x, df)

    quantile = dist.quantile(x)
    self.assertEqual(quantile.shape, (batch_size, 13))
    self.assertAllClose(self.evaluate(quantile), expected_quantile)

  def testChi2Mean(self):
    df_v = np.array([1., 3, 5], dtype=np.float64)
    expected_mean = stats.chi2.mean(df_v)
    dist = chi2.Chi2(df=df_v, validate_args=True)
    self.assertEqual(dist.mean().shape, (3,))
    self.assertAllClose(self.evaluate(dist.mean()), expected_mean)

  def testChi2Variance(self):
    df_v = np.array([1., 3, 5], np.float64)
    expected_variances = stats.chi2.var(df_v)
    dist = chi2.Chi2(df=df_v, validate_args=True)
    self.assertEqual(dist.variance().shape, (3,))
    self.assertAllClose(self.evaluate(dist.variance()), expected_variances)

  def testChi2Entropy(self):
    df_v = np.array([1., 3, 5], dtype=np.float64)
    expected_entropy = stats.chi2.entropy(df_v)
    dist = chi2.Chi2(df=df_v, validate_args=True)
    self.assertEqual(dist.entropy().shape, (3,))
    self.assertAllClose(self.evaluate(dist.entropy()), expected_entropy)

  def testChi2Chi2KL(self):
    a_df = np.arange(1.0, 10.0)
    b_df = np.arange(1.0, 10.0)

    # This reshape is intended to expand the number of test cases.
    a_df = a_df.reshape((len(a_df), 1))
    b_df = b_df.reshape((1, len(b_df)))

    a = chi2.Chi2(df=a_df, validate_args=True)
    b = chi2.Chi2(df=b_df, validate_args=True)

    # Consistent with
    # http://www.mast.queensu.ca/~communications/Papers/gil-msc11.pdf, page 110
    true_kl = (special.gammaln(b_df / 2.0) - special.gammaln(a_df / 2.0) +
               (a_df - b_df) / 2.0 * special.digamma(a_df / 2.0))

    kl = kullback_leibler.kl_divergence(a, b)

    x = a.sample(int(1e5), seed=test_util.test_seed())
    kl_samples = a.log_prob(x) - b.log_prob(x)

    kl_, kl_samples_ = self.evaluate([kl, kl_samples])
    self.assertAllClose(kl_, true_kl, atol=0., rtol=5e-13)
    self.assertAllMeansClose(kl_samples_, true_kl, axis=0, atol=0., rtol=.08)

    zero_kl = kullback_leibler.kl_divergence(a, a)
    true_zero_kl_, zero_kl_ = self.evaluate([tf.zeros_like(zero_kl), zero_kl])
    self.assertAllEqual(true_zero_kl_, zero_kl_)

  @test_util.tf_tape_safety_test
  def testGradientThroughParams(self):
    df = tf.Variable(19.43, dtype=tf.float64)
    d = chi2.Chi2(df, validate_args=True)
    with tf.GradientTape() as tape:
      loss = -d.log_prob([1., 2., 3.])
    grad = tape.gradient(loss, d.trainable_variables)
    self.assertLen(grad, 1)
    self.assertAllNotNone(grad)

  @test_util.tf_tape_safety_test
  def testGradientThroughNonVariableParams(self):
    df = tf.convert_to_tensor(13.37)
    d = chi2.Chi2(df, validate_args=True)
    with tf.GradientTape() as tape:
      tape.watch(d.df)
      loss = -d.log_prob([1., 2., 3.])
    grad = tape.gradient(loss, [d.df])
    self.assertLen(grad, 1)
    self.assertAllNotNone(grad)

  def testAssertsPositiveDf(self):
    df = tf.Variable([1., 2., -3.])
    with self.assertRaisesOpError('Argument `df` must be positive.'):
      d = chi2.Chi2(df, validate_args=True)
      self.evaluate([v.initializer for v in d.variables])
      self.evaluate(d.sample(seed=test_util.test_seed()))

  def testAssertsPositiveDfAfterMutation(self):
    df = tf.Variable([1., 2., 3.])
    d = chi2.Chi2(df, validate_args=True)
    self.evaluate([v.initializer for v in d.variables])
    with self.assertRaisesOpError('Argument `df` must be positive.'):
      with tf.control_dependencies([df.assign([1., 2., -3.])]):
        self.evaluate(d.mean())

  def testSupportBijectorOutsideRange(self):
    df = np.array([2., 4., 7.])
    dist = chi2.Chi2(df, validate_args=True)
    x = np.array([-8.3, -0.4, -1e-6])
    bijector_inverse_x = dist.experimental_default_event_space_bijector(
        ).inverse(x)
    self.assertAllNan(self.evaluate(bijector_inverse_x))

if __name__ == '__main__':
  test_util.main()
