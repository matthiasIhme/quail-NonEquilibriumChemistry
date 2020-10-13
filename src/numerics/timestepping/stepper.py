# ------------------------------------------------------------------------ #
#
#       File : src/numerics/timestepping/stepper.py
#
#       Contains class definitions for timestepping methods.
#      
# ------------------------------------------------------------------------ #
from abc import ABC, abstractmethod
import numpy as np 
from scipy.optimize import fsolve, root

from general import StepperType, ODESolverType

import numerics.basis.tools as basis_tools
import numerics.helpers.helpers as helpers
import numerics.timestepping.tools as stepper_tools
import numerics.timestepping.ode as ode

import solver.tools as solver_tools


class StepperBase(ABC):
	'''
	This is an abstract base class used to represent time stepping schemes. The current build supports the following time
	schemes:

		Explicit Schemes:
		-----------------
		- Forward Euler (FE)
		- 4th-order Runge Kutta (RK4)
		- Low storage 4th-order Runge Kutta (LSRK4)
		- Strong-stability preserving 3rd-order Runge Kutta (SSPRK3)
		- Arbitrary DERivatives in space and time (ADER) 
			-> used in tandem with ADERDG solver
		
		Operator Splitting Type Schemes:
		--------------------------------
		- Strang Splitting (Strang)
		- Simpler Splitting (Simpler)

		ODE Solvers for Splitting Schemes:
		----------------------------------
		- Backward Difference (BDF1)
		- Trapezoidal Scheme (Trapezoidal)


	Attributes:
	-----------
	R: numpy array [num_elems, nb, ns]
		residual array
	dt: float
		time-step for the solution
	num_time_steps: int
		number of time steps for the given solution's FinalTime
	get_time_step: method
		method to obtain dt given input decks logic (CFL-based vs # of 
		timesteps, etc...)
	balance_const: numpy array (shaped like R)
		balancing constant array used only with the Simpler splitting scheme
	
	Abstract Methods:
	-----------------
	take_time_step
		method that takes a given time step for the solver depending on the 
		selected time-stepping scheme
	'''
	def __init__(self, U):
		self.R = np.zeros_like(U)
		self.dt = 0.
		self.num_time_steps = 0
		self.get_time_step = None
		self.balance_const = None # kept as None unless set by Simpler scheme

	def __repr__(self):
		return '{self.__class__.__name__}(TimeStep={self.dt})'.format( \
			self=self)
	
	@abstractmethod
	def take_time_step(self, solver):
		'''
		Takes a time step using the specified time-stepping scheme for the
		solution.

		Inputs:
		-------
		    solver: solver object (e.g., DG, ADERDG, etc...)

		Outputs:
		-------- 
			R: Updated residual vector [num_elems, nb, ns]
			U: Updates the solution vector [num_elems, nb, ns]
		'''
		pass


class FE(StepperBase):
	'''
	Forward Euler (FE) method inherits attributes from StepperBase. See 
	StepperBase for detailed comments of methods and attributes.

	Additional methods and attributes are commented below.
	''' 
	def take_time_step(self, solver):
		physics = solver.physics
		mesh = solver.mesh
		U = physics.U

		R = self.R 
		R = solver.get_residual(U, R)
		dU = solver_tools.mult_inv_mass_matrix(mesh, solver, self.dt, R)
		U += dU

		solver.apply_limiter(U)

		return R # [num_elems, nb, ns]


class RK4(StepperBase):
	'''
	4th-order Runge Kutta (RK4) method inherits attributes from StepperBase. 
	See StepperBase for detailed comments of methods and attributes.

	Additional methods and attributes are commented below.
	''' 
	def take_time_step(self, solver):
		physics = solver.physics
		mesh = solver.mesh
		U = physics.U

		R = self.R

		# First stage
		R = solver.get_residual(U, R)
		dU1 = solver_tools.mult_inv_mass_matrix(mesh, solver, self.dt, R)
		Utemp = U + 0.5*dU1
		solver.apply_limiter(Utemp)

		# Second stage
		solver.time += self.dt/2.
		R = solver.get_residual(Utemp, R)
		dU2 = solver_tools.mult_inv_mass_matrix(mesh, solver, self.dt, R)
		Utemp = U + 0.5*dU2
		solver.apply_limiter(Utemp)

		# Third stage
		R = solver.get_residual(Utemp, R)
		dU3 = solver_tools.mult_inv_mass_matrix(mesh, solver, self.dt, R)
		Utemp = U + dU3
		solver.apply_limiter(Utemp)

		# Fourth stage
		solver.time += self.dt/2.
		R = solver.get_residual(Utemp, R)
		dU4 = solver_tools.mult_inv_mass_matrix(mesh, solver, self.dt, R)
		dU = 1./6.*(dU1 + 2.*dU2 + 2.*dU3 + dU4)
		U += dU
		solver.apply_limiter(U)

		return R # [num_elems, nb, ns]


class LSRK4(StepperBase):
	'''
	Low storage 4th-order Runge Kutta (RK4) method inherits attributes from 
	StepperBase. See StepperBase for detailed comments of methods and 
	attributes.

	Reference:

	M. H. Carpenter, C. Kennedy, "Fourth-order 2N-storage Runge-Kutta schemes,"" NASA Report TM 109112, NASA Langley Research Center, 1994.

	Additional methods and attributes are commented below.
	''' 
	def __init__(self, U):
		super().__init__(U)
		'''
		Additional Attributes:
		----------------------
		rk4a: numpy array
			coefficients for LSRK4 scheme
		rk4b: numpy array
			coefficients for LSRK4 scheme
		rk4c: numpy array
			coefficients for LSRK4 scheme
		nstages: int
			number of stages in scheme
		dU: numpy array
			change in solution array in each stage
				(shape: [num_elems, nb, ns])
		'''
		self.rk4a = np.array([0.0, -567301805773.0/1357537059087.0, 
		    -2404267990393.0/2016746695238.0, 
		    -3550918686646.0/2091501179385.0,
		    -1275806237668.0/842570457699.0])
		self.rk4b = np.array([1432997174477.0/9575080441755.0,
		    5161836677717.0/13612068292357.0,
		    1720146321549.0/2090206949498.0,
		    3134564353537.0/4481467310338.0,
		    2277821191437.0/14882151754819.0])
		self.rk4c = np.array([0.0, 1432997174477.0/9575080441755.0, 
		    2526269341429.0/6820363962896.0, 
		    2006345519317.0/3224310063776.0, 
		    2802321613138.0/2924317926251.0])
		self.nstages = 5
		self.dU = np.zeros_like(U)

	def take_time_step(self, solver):
		physics = solver.physics
		mesh = solver.mesh
		U = physics.U

		R = self.R
		dU = self.dU

		Time = solver.time
		for istage in range(self.nstages):
			dt = self.dt
			solver.time = Time + self.rk4c[istage]*dt
			R = solver.get_residual(U, R)

			dUtemp = solver_tools.mult_inv_mass_matrix(mesh, solver, dt, R)
			dU *= self.rk4a[istage]
			dU += dUtemp

			U += self.rk4b[istage]*dU
			solver.apply_limiter(U)

		return R # [num_elems, nb, ns]


class SSPRK3(StepperBase):
	'''
	Low storage 3rd-order strong stability preserving Runge Kutta (SSPRK3) 
	method inherits attributes from StepperBase. See StepperBase for 
	detailed comments of methods and attributes.

	Reference: 

	R. J. Spiteri, S., Ruuth, "A new class of optimal high-order 
	strong-stability-preserving time discrtization methods". SIAM Journal on 
	Numerical Analysis. Vol. 2, Num. 2, pp. 469-491. 2002

	Additional methods and attributes are commented below.
	''' 
	def __init__(self, U):
		super().__init__(U)
		'''
		Additional Attributes:
		----------------------
		ssprk3a: numpy array
			coefficients for SSPRK3 scheme
		ssprk3b: numpy array 
			coefficients for SSPRK3 scheme
		nstages: int
			number of stages in scheme
		dU: numpy array
			change in solution array in each stage
				(shape: [num_elems, nb, ns])
		'''
		self.ssprk3a = np.array([0.0, -2.60810978953486, -0.08977353434746, 
				-0.60081019321053, -0.72939715170280])
		self.ssprk3b = np.array([0.67892607116139, 0.20654657933371, 
				0.27959340290485, 0.31738259840613, 0.30319904778284])
		self.nstages = 5
		self.dU = np.zeros_like(U)

	def take_time_step(self, solver):
		physics = solver.physics
		mesh = solver.mesh
		U = physics.U

		R = self.R
		dU = self.dU

		Time = solver.time
		for istage in range(self.nstages):
			dt = self.dt
			solver.time = Time + dt
			R = solver.get_residual(U, R)
			dUtemp = solver_tools.mult_inv_mass_matrix(mesh, solver, dt, R)
			dU *= self.ssprk3a[istage]
			dU += dUtemp

			U += self.ssprk3b[istage]*dU
			solver.apply_limiter(U)

		return R # [num_elems, nb, ns]


class ADER(StepperBase):
	'''
	Arbitrary DERivatives in space and time (ADER) scheme inherits 
	attributes from StepperBase. See StepperBase for detailed comments of 
	methods and attributes.

	Reference: 

	Dumbser, M., Enaux, C., and Toro, E.F., "Finite volume schemes of very 
	high order of accuracy for stiff hyperbolic balance laws". Journal of 
	Computational Physics. Vol. 227, Num. 8, pp. 3971 - 4001, 2008.

	Additional methods and attributes are commented below. Additional 
	information on the ADER scheme can be found in the documentation.
	''' 	
	def take_time_step(self, solver):
		physics = solver.physics
		mesh = solver.mesh
		W = physics.U
		Up = physics.U_pred

		R = self.R

		# Prediction step
		Up = solver.calculate_predictor_step(self.dt, W, Up)

		# Correction step
		R = solver.get_residual(Up, R)

		dU = solver_tools.mult_inv_mass_matrix(mesh, solver, self.dt/2., R)

		W += dU
		solver.apply_limiter(W)

		return R # [num_elems, nb, ns]


class Strang(StepperBase, ode.ODESolvers):
	'''
	The Strang operator splitting scheme inherits attributes from 
	StepperBase and ODESolvers (in ode.py). See StepperBase and ODESolvers 
	for detailed comments of methods and attributes.

	Reference: 

	Strang, G. "On the Construction and Comparison of Difference Schemes". 
	SIAM Journal of Numerical Analysis. Vol. 5, Num. 3, 1968.

	Additional methods and attributes are commented below.
	''' 	
	def set_split_schemes(self, explicit, implicit, U):
		'''
		Specifies the explicit and implicit schemes to be used in the
		operator splitting technique

		Inputs:
		-------
		    explicit: name of chosen explicit scheme from params
		    implicit: name of chosen implicit (ODE) solver from params
		    U: solution state vector used to initialize solver 
		    	[num_elems, nb, ns]

		Outputs:
		-------- 
		    explicit: stepper object instantiation for explicit scheme
		    implicit: stepper object instantiation for ODE solver
		'''		
		param = {"TimeStepper":explicit}
		# call set_stepper from stepper tools for the explicit scheme
		self.explicit = stepper_tools.set_stepper(param, U)

		if ODESolverType[implicit] == ODESolverType.BDF1:
			self.implicit = ode.ODESolvers.BDF1(U)
		elif ODESolverType[implicit] == ODESolverType.Trapezoidal:
			self.implicit = ode.ODESolvers.Trapezoidal(U)
		else:
			raise NotImplementedError("Time scheme not supported")

	def take_time_step(self, solver):
		physics = solver.physics
		mesh  = solver.mesh
		U = physics.U

		explicit = self.explicit
		explicit.dt = self.dt/2.
		implicit = self.implicit
		implicit.dt = self.dt

		# First: take the half-step for the inviscid flux only
		solver.params["SourceSwitch"] = False
		R1 = explicit.take_time_step(solver)

		# Second: take the implicit full step for the source term.
		solver.params["SourceSwitch"] = True
		solver.params["ConvFluxSwitch"] = False

		R2 = implicit.take_time_step(solver)

		# Third: take the second half-step for the inviscid flux only.
		solver.params["SourceSwitch"] = False
		solver.params["ConvFluxSwitch"] = True
		R3 = explicit.take_time_step(solver)

		return R3 # [num_elems, nb, ns]


class Simpler(Strang):
	'''
	The Simpler balanced operator splitting scheme inherits attributes from 
	Strang. See Strang for detailed comments of methods and attributes.

	Reference: 

	Wu, H., Ma, P. and Ihme, M. "Efficient time-stepping techniques for 
	simulating turbulent reactive flows with stiff chemistry". Computer 
	Physics Communications. Vol. 243, pp. 81 - 96, 2019.

	Additional methods and attributes are commented below.
	''' 	
	def take_time_step(self, solver):
		physics = solver.physics
		mesh  = solver.mesh
		U = physics.U

		explicit = self.explicit
		explicit.dt = self.dt/2.
		implicit = self.implicit
		implicit.dt = self.dt
		
		solver.params["SourceSwitch"] = False
		R = self.R 

		# First: calculate the balance constant
		# Note: we skip the first explicit step as it is in equillibrium by 
		# 		definition
		self.balance_const = None
		balance_const = -1.*solver.get_residual(U, R)
		self.balance_const = -1.*balance_const

		# Second: take the implicit full step for the source term.
		solver.params["SourceSwitch"] = True
		solver.params["ConvFluxSwitch"] = False
		R2 = implicit.take_time_step(solver)

		# Third: take the second half-step for the inviscid flux only.
		solver.params["SourceSwitch"] = False
		solver.params["ConvFluxSwitch"] = True
		self.balance_const = balance_const
		R3 = explicit.take_time_step(solver)

		return R3 # [num_elems, nb, ns]