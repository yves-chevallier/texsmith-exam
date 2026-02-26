---
title: Analysis IV
subtitle: Problem Set 4
author: Prof. J. Douchet
date: 2010-03-18
problem-label: Exercise
compact: true
next_page_advice: false
language: en
course: MATH 401
titlepage: minimal
points: false
version: git
rules:
  - Write your **last name** and **first name** on the first page.
  - Write **legibly**, using a pen or a soft pencil.
  - Answer the questions in the appropriate spaces.
  - Review all your answers before handing in your work.
  - Turn in all pages of this written assignment.
  - Answers on scratch paper **are not accepted**.
  - No means of communication are allowed.

---

## -

Let $f : \mathbb{R} \to \mathbb{R}$ be the continuous function defined on $\mathbb{R}^*$ by $f(t) = \frac{\sin t}{t}$.

### - { points=5 }

Compute

$$
g(x) = \frac{1}{\sqrt{2\pi}} \int_{-\infty}^{+\infty} f(t) \, e^{-ixt} \, dt
$$

!!! solution { box=6cm }

    Since $f$ is continuous and even, we have (see the Dirichlet integral):

    $$
    \frac{1}{\sqrt{2\pi}} \int_{-\infty}^{+\infty} \frac{\sin t}{t} e^{-ixt} \, dt
    =
    \frac{2}{\sqrt{2\pi}} \int_{0}^{+\infty} \frac{\sin t}{t} \cos(xt) \, dt.
    $$

    Use the trigonometric identity:

    $$
    \sin t \cos(xt)
    =
    \frac{1}{2}
    \left[
    \sin\big((1+x)t\big)
    +
    \sin\big((1-x)t\big)
    \right].
    $$

    Therefore,
    $$
    \frac{1}{\sqrt{2\pi}}
    \left(
    \int_{0}^{+\infty} \frac{\sin\big((1+x)t\big)}{t} \, dt
    +
    \int_{0}^{+\infty} \frac{\sin\big((1-x)t\big)}{t} \, dt
    \right)
    $$

    Using the Dirichlet integral:

    $$
    \int_{0}^{+\infty} \frac{\sin(at)}{t} \, dt
    =
    \begin{cases}
    \frac{\pi}{2} & \text{if } a > 0, \\
    0 & \text{if } a = 0, \\
    -\frac{\pi}{2} & \text{if } a < 0,
    \end{cases}
    $$

    we finally obtain:

    $$
    \frac{1}{\sqrt{2\pi}} \int_{-\infty}^{+\infty} \frac{\sin t}{t} e^{-ixt} \, dt
    =
    \begin{cases}
    \sqrt{\frac{\pi}{2}} & \text{if } |x| < 1, \\[6pt]
    \frac{1}{2}\sqrt{\frac{\pi}{2}} & \text{if } |x| = 1, \\[6pt]
    0 & \text{if } |x| > 1.
    \end{cases}
    $$

### - { points=3 }

Explain why the result of Theorem 15.2 (i) does not apply here.

!!! solution { lines=2 }

    The function $g$ is not continuous even though $f$ is.

    This is because the hypothesis

    $$
    \int_{-\infty}^{+\infty} |f(t)|, dt < +\infty
    $$

    of Theorem 15.2 is not satisfied.

## -

Let $H : \mathbb{R} \to \mathbb{R}$ be the Heaviside function defined by

$$
H(x) =
\begin{cases}
0 & \text{if } x < 0, \\
1 & \text{if } x \ge 0,
\end{cases}
$$

and let $f : \mathbb{R} \to \mathbb{R}$ be a function such that
$$
\int_{-\infty}^{+\infty} |f(t)| \, dt < +\infty.
$$

### - { points=10 }

Compute

$$
\frac{d}{dx}(H * f).
$$

!!! solution { box=6cm }

    Compute the derivative of the convolution:

    $$
    \frac{d}{dx}(H * f)(x)
    =
    \frac{d}{dx}\int_{-\infty}^{+\infty} H(x-t) f(t) \, dt.
    $$

    Since $H(x-t)=1$ for $t \le x$ and $0$ otherwise,

    $$
    \int_{-\infty}^{+\infty} H(x-t) f(t) \, dt
    =
    \int_{-\infty}^{x} f(t) \, dt.
    $$

    Therefore,

    $$
    \frac{d}{dx}(H * f)(x)
    =
    f(x),
    \qquad x \in \mathbb{R}.
    $$

### - { points=5 }

Compute for every integer $n \ge 2$:

$$
H_n = \underbrace{H * \cdots * H}_{n \text{ times}}.
$$

!!! solution { box=10cm }

    We prove by induction that for all $n \ge 2$:

    $$
    H_n(x)=
    \begin{cases}
    \dfrac{x^{n-1}}{(n-1)!} & \text{if } x>0, \\[6pt]
    0 & \text{if } x\le 0.
    \end{cases}
    $$

    Initialization ($n=2$):

    $$
    H_2(x)=\int_{-\infty}^{+\infty} H(x-t) H(t) \, dt.
    $$

    Since $H(t)=0$ for $t\le 0$ and $H(x-t)=0$ for $t>x$, this becomes

    $$
    H_2(x)=\int_{0}^{x} 1 \, dt
    =
    \begin{cases}
    x & \text{if } x>0, \\
    0 & \text{if } x\le 0,
    \end{cases}
    $$

    which matches
    $$
    \frac{x^{2-1}}{(2-1)!}=x.
    $$

    Inductive step:

    Assume the formula holds for some $n \ge 2$. Then

    $$
    H_{n+1}(x)=H*H_n(x)=\int_{-\infty}^{+\infty} H(x-t) H_n(t) \, dt
    =
    \int_{-\infty}^{x} H_n(t) \, dt.
    $$

    If $x\le 0$, then $H_n(t)=0$ and $H_{n+1}(x)=0$.

    If $x>0$, then

    $$
    H_{n+1}(x)=\int_{0}^{x} \frac{t^{n-1}}{(n-1)!} \, dt
    =
    \frac{1}{(n-1)!}\cdot \frac{x^n}{n}
    =
    \frac{x^n}{n!}.
    $$

    Therefore,

    $$
    H_{n+1}(x)=
    \begin{cases}
    \dfrac{x^{n}}{n!} & \text{if } x>0, \\[6pt]
    0 & \text{if } x\le 0,
    \end{cases}
    $$

    which completes the proof.

## - { points=5 }

Let $f : \mathbb{R} \to \mathbb{R}$ be the function defined by
$$
f(t) = e^{-t^2}.
$$

Compute $f * f$.

!!! solution { box=6cm }

    For any $x \in \mathbb{R}$,

    $$
    (f * f)(x)
    =
    \int_{-\infty}^{+\infty} e^{-(x-t)^2} e^{-t^2} \, dt
    =
    e^{-\frac{x^2}{2}}
    \int_{-\infty}^{+\infty} e^{-2\left(\frac{x}{2}-t\right)^2} \, dt
    =
    e^{-\frac{x^2}{2}} \sqrt{\frac{\pi}{2}}.
    $$

## - { points=10 }

Find a solution of

$$
y(x) + \int_0^{+\infty} \left( y'(x - t) + y(x - t) \right) e^{-t}, dt
= -2x e^{-x^2}, \quad x \in \mathbb{R}.
$$

!!! solution { box=10cm }

    Let $g, f : \mathbb{R} \to \mathbb{R}$ be defined by

    $$
    f(x)=
    \begin{cases}
    e^{-x} & \text{if } x \ge 0, \\
    0 & \text{if } x < 0,
    \end{cases}
    \qquad
    \text{and}
    \qquad
    g(x)=-2x e^{-x^2}.
    $$

    For all $x \in \mathbb{R}$,

    $$
    f * (y' + y)(x)
    =
    \int_{0}^{+\infty} \big( y'(x-t) + y(x-t) \big) e^{-t} \, dt,
    $$

    so by linearity of the Fourier transform,

    $$
    \begin{aligned}
    \mathcal{F}\big( y + f * (y' + y) \big)(\alpha)
    &=
    \mathcal{F}(y)(\alpha)
    +
    \mathcal{F}\big( f * (y' + y) \big)(\alpha) \\
    &=
    \mathcal{F}(y)(\alpha)
    +
    \sqrt{2\pi}\,\mathcal{F}(f)(\alpha)
    \big(
    \mathcal{F}(y')(\alpha)
    +
    \mathcal{F}(y)(\alpha)
    \big) \\
    &=
    \mathcal{F}(y)(\alpha)
    +
    \sqrt{2\pi}
    \frac{1}{\sqrt{2\pi}}
    \frac{1}{1+i\alpha}
    \big(
    i\alpha \mathcal{F}(y)(\alpha)
    +
    \mathcal{F}(y)(\alpha)
    \big) \\
    &=
    2 \mathcal{F}(y)(\alpha).
    \end{aligned}
    $$

    Finally, since we want

    $$
    2\mathcal{F}(y)=\mathcal{F}(g),
    $$

    it is enough to take

    $$
    y(x)=\frac{1}{2}g(x)=-x e^{-x^2}.
    $$
