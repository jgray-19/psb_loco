# Chroma investigation

The figures compare the two tune-matched settings

$$
(Q_x,Q_y)=(4.171,4.229),\qquad
(Q_x,Q_y)=(4.233,4.128).
$$

For each setting, we matched a MAD model to the measured tunes, this is the "model" referred to here and on all the figures.

Blue uses momentum inferred by projecting the closed-orbit change at different RF settings onto the matched model dispersion,

$$
\left(\frac{\Delta p}{p}\right)_{\!\rm orbit}
=\frac{\sum_i D_{x,i}\left(x_i-x_{i,0}\right)}
       {\sum_i D_{x,i}^{,2}}.
$$

The sum runs over the BPMs; $x_i-x_{i,0}$ is the orbit change from the nominal
RF setting and $D_{x,i}$ is the model horizontal dispersion.

Orange uses the Qmeter2 `Dp/p`. Green recalculates `Dp/p` using the measured `BfC` and `Frev`, and
model $\rho$ and $\gamma_t$. All error bars are standard deviations.

A guessed 10% relative uncertainty in the model dispersion is shown and propagated through the blue calibration.

All measurements of the closed orbit were made using the Multiturn application with an intensity of 1.7e11 protons and a gain of 2e10.
The closed orbit had an RMS of 0.99 mm in x and 1.2 mm in y.

Tune slopes are fitted directly against physical $\Delta p/p$ and reported as
$Q_x'$ and $Q_y'$. The revolution-frequency fit uses

$$
\frac{f_{\rm rev}-f_0}{f_0}
=\left(\frac{1}{\gamma^2}-\alpha_p\right)\frac{\Delta p}{p}
$$

The uncertainty in $1/\gamma^2$ assumes a guessed 1% relative kinetic-energy uncertainty.
