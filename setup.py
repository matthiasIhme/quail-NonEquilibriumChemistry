from setuptools import setup

setup(
   name='Quail',
   version='1.0',
   description='Quail is a lightweight, open-source discontinuous Galerkin code written in Python for teaching and prototyping. Currently, Quail solves first-order nonlinear hyperbolic systems of partial differential equations.',
   author='Eric Ching, Brett Bornhoft, and Ali Lasemi',
   author_email='bornhoft@stanford.edu',
   packages=setuptools.find_namespace_packages(),  #automatically discover submodules
   install_requires=['numpy', 'scipy', 'matplotlib'], #external packages as dependencies

   entry_points={
      'console_scripts': [
         'quail = quail.main:main',
      ]
   },
)
