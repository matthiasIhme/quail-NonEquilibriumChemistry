# ------------------------------------------------------------------------ #
#
#       quail: A lightweight discontinuous Galerkin code for
#              teaching and prototyping
#		<https://github.com/IhmeGroup/quail>
#
#		Copyright (C) 2020-2021
#
#       This program is distributed under the terms of the GNU
#		General Public License v3.0. You should have received a copy
#       of the GNU General Public License along with this program.
#		If not, see <https://www.gnu.org/licenses/>.
#
# ------------------------------------------------------------------------ #

# ------------------------------------------------------------------------ #
#
#       File : src/physics/euler/functions.py
#
#       Contains definitions of Functions, boundary conditions, and source
#       terms for the Euler equations.
#
# ------------------------------------------------------------------------ #
from enum import Enum, auto
import numpy as np
from scipy.optimize import fsolve, root

from quail import errors, general

from quail.physics.base.data import (FcnBase, BCWeakRiemann,
        BCWeakPrescribed, SourceBase, ConvNumFluxBase)


class FcnType(Enum):
    '''
    Enum class that stores the types of analytical functions for initial
    conditions, exact solutions, and/or boundary conditions. These
    functions are specific to the available Euler equation sets.
    '''
    SmoothIsentropicFlow = auto()
    MovingShock = auto()
    IsentropicVortex = auto()
    DensityWave = auto()
    RiemannProblem = auto()
    TaylorGreenVortex = auto()
    ShuOsherProblem = auto()
    GravityRiemann = auto()

class BCType(Enum):
    '''
    Enum class that stores the types of boundary conditions. These
    boundary conditions are specific to the available Euler equation sets.
    '''
    SlipWall = auto()
    SlipWallRiemann = auto()
    PressureOutlet = auto()
    AdiabaticWall = auto()
    IsothermalWall = auto()
    IsothermalWallRiemann = auto()


class SourceType(Enum):
    '''
    Enum class that stores the types of source terms. These
    source terms are specific to the available Euler equation sets.
    '''
    StiffFriction = auto()
    TaylorGreenSource = auto()
    GravitySource = auto()


class ConvNumFluxType(Enum):
    '''
    Enum class that stores the types of convective numerical fluxes. These
    numerical fluxes are specific to the available Euler equation sets.
    '''
    Roe = auto()
    HLLC = auto()


'''
---------------
State functions
---------------
These classes inherit from the FcnBase class. See FcnBase for detailed
comments of attributes and methods. Information specific to the
corresponding child classes can be found below. These classes should
correspond to the FcnType enum members above.
'''

class SmoothIsentropicFlow(FcnBase):
    '''
    Smooth isentropic flow problem from the following references:
        [1] J. Cheng, C.-W. Shu, "Positivity-preserving Lagrangian
        scheme for multi-material compressible flow," Journal of
        Computational Physics, 257:143-168, 2014.
        [2] R. Abgrall, P. Bacigaluppi, S. Tokareva, "High-order residual
        distribution scheme for the time-dependent Euler equations of fluid
        dynamics," Computers and Mathematics with Applications, 78:274-297,
        2019.

    Attributes:
    -----------
    a: float
        parameter that controls magnitude of sinusoidal profile
    '''
    def __init__(self, a=0.9):
        '''
        This method initializes the attributes.

        Parameters
        ----------
            a: parameter that controls magnitude of sinusoidal profile

        Returns
        -------
            self: attributes initialized
        '''
        if a > 1:
            raise ValueError
        self.a = a

    def get_state(self, physics, x, t):
        a = self.a
        gamma = physics.thermo.gamma
        irho, irhou, irhoE = physics.get_state_indices()

        # Lambda functions
        rho0 = lambda x, a: 1. + a*np.sin(np.pi*x)
        pressure = lambda rho, gamma: rho**gamma
        rho = lambda x1, x2, a: 0.5*(rho0(x1, a) + rho0(x2, a))
        vel = lambda x1, x2, a: np.sqrt(3)*(rho(x1, x2, a) - rho0(x1, a))

        # Nonlinear equations to be solved
        f1 = lambda x1, x, t, a: x + np.sqrt(3)*rho0(x1, a)*t - x1
        f2 = lambda x2, x, t, a: x - np.sqrt(3)*rho0(x2, a)*t - x2

        xr_elems = x[:,:,0]

        Uq = np.zeros(xr_elems.shape + (physics.NUM_STATE_VARS,))

        for elem_ID in range(x.shape[0]):
            xr = xr_elems[elem_ID,:]
            # Solve above nonlinear equations for x1 and x2
            x1 = fsolve(f1, 0.*xr, (xr, t, a))
            if np.abs(x1.any()) > 1.: raise Exception("x1 = %g out of range" %
                    (x1))
            x2 = fsolve(f2, 0.*xr, (xr, t, a))
            if np.abs(x2.any()) > 1.: raise Exception("x2 = %g out of range" %
                    (x2))

            # State
            den = rho(x1, x2, a)
            u = vel(x1, x2, a)
            p = pressure(den, gamma)
            rhoE = p/(gamma - 1.) + 0.5*den*u*u

            # Store
            Uq[elem_ID, :, irho] = den
            Uq[elem_ID, :, irhou] = den*u
            Uq[elem_ID, :, irhoE] = rhoE

        return Uq # [ne, nq, ns]


class MovingShock(FcnBase):
    '''
    Moving shock problem.

    Attributes:
    -----------
    M: float
        Mach number
    xshock: float
        initial location of shock
    '''
    def __init__(self, M=5.0, xshock=0.2):
        '''
        This method initializes the attributes.

        Parameters
        ----------
            M: Mach number
            xshock: initial location of shock

        Returns
        -------
            self: attributes initialized
        '''
        self.M = M
        self.xshock = xshock

    def get_state(self, physics, x, t):
        # Unpack
        M = self.M
        xshock = self.xshock

        srho, srhou, srhoE = physics.get_state_slices()

        gamma = physics.thermo.gamma

        ''' Pre-shock state '''
        rho1 = 1.
        p1 = 1.e5
        u1 = 0.

        ''' Update xshock based on shock speed '''
        a1 = np.sqrt(gamma*p1/rho1)
        W = M*a1
        us = u1 + W # shock speed in lab frame
        xshock = xshock + us*t

        ''' Post-shock state '''
        rho2 = (gamma + 1.)*M**2./((gamma - 1.)*M**2. + 2.)*rho1
        p2 = (2.*gamma*M**2. - (gamma - 1.))/(gamma + 1.)*p1
        # To get velocity, first work in reference frame fixed to shock
        ux = W
        uy = ux*rho1/rho2
        # Convert back to lab frame
        u2 = W + u1 - uy

        ''' Fill state '''
        Uq = np.zeros([x.shape[0], x.shape[1], physics.NUM_STATE_VARS])

        for elem_ID in range(Uq.shape[0]):
            ileft = (x[elem_ID] <= xshock).reshape(-1)
            iright = (x[elem_ID] > xshock).reshape(-1)
            # Density
            Uq[elem_ID, iright, srho] = rho1
            Uq[elem_ID, ileft, srho] = rho2
            # Momentum
            Uq[elem_ID, iright, srhou] = rho1*u1
            Uq[elem_ID, ileft, srhou] = rho2*u2
            # Energy
            Uq[elem_ID, iright, srhoE] = p1/(gamma - 1.) + 0.5*rho1*u1*u1
            Uq[elem_ID, ileft, srhoE] = p2/(gamma - 1.) + 0.5*rho2*u2*u2

        return Uq # [ne, nq, ns]


class IsentropicVortex(FcnBase):
    '''
    Isentropic vortex problem from the following reference:
        [1] C.-W. Shu, "Essentially non-oscillatory and weighted essentially
        non-oscillatory schemes for hyperbolic conservation laws," in:
        Advanced Numerical Approximation of Nonlinear Hyperbolic Equations,
        Springer-Verlag, Berlin/New York, 1998, pp. 325–432.

    Attributes:
    -----------
    rhob: float
        base density
    ub: float
        base x-velocity
    vb: float
        base y-velocity
    pb: float
        base pressure
    vs: float
        vortex strength
    '''
    def __init__(self, rhob=1., ub=1., vb=1., pb=1., vs=5.):
        '''
        This method initializes the attributes.

        Parameters
        ----------
            rhob: base density
            ub: base x-velocity
            vb: base y-velocity
            pb: base pressure
            vs: vortex strength

        Returns
        -------
            self: attributes initialized
        '''
        self.rhob = rhob
        self.ub = ub
        self.vb = vb
        self.pb = pb
        self.vs = vs

    def get_state(self, physics, x, t):
        Uq = np.zeros([x.shape[0], x.shape[1], physics.NUM_STATE_VARS])
        gamma = physics.thermo.gamma
        Rg = physics.thermo.R

        ''' Base flow '''
        # Density
        rhob = self.rhob
        # x-velocity
        ub = self.ub
        # y-velocity
        vb = self.vb
        # Pressure
        pb = self.pb
        # Vortex strength
        vs = self.vs
        # Make sure Rg is 1
        if Rg != 1.:
            raise ValueError

        # Base temperature
        Tb = pb/(rhob*Rg)

        # Entropy
        s = pb/rhob**gamma

        # Track center of vortex
        xr = x[:, :, 0] - ub*t
        yr = x[:, :, 1] - vb*t
        r = np.sqrt(xr**2. + yr**2.)

        # Perturbations
        dU = vs/(2.*np.pi)*np.exp(0.5*(1-r**2.))
        du = dU*-yr
        dv = dU*xr

        dT = -(gamma - 1.)*vs**2./(8.*gamma*np.pi**2.)*np.exp(1. - r**2.)

        u = ub + du
        v = vb + dv
        T = Tb + dT

        # Convert to conservative variables
        rho = np.power(T/s, 1./(gamma - 1.))
        rhou = rho*u
        rhov = rho*v
        rhoE = rho*Rg/(gamma - 1.)*T + 0.5*(rhou*rhou + rhov*rhov)/rho

        Uq[:, :, 0] = rho
        Uq[:, :, 1] = rhou
        Uq[:, :, 2] = rhov
        Uq[:, :, 3] = rhoE

        return Uq # [ne, nq, ns]


class DensityWave(FcnBase):
    '''
    Simple smooth density wave.

    Attributes:
    -----------
    p: float
        pressure
    '''
    def __init__(self, p=1.0):
        '''
        This method initializes the attributes.

        Parameters
        ----------
            p: pressure

        Returns
        -------
            self: attributes initialized
        '''
        self.p = p

    def get_state(self, physics, x, t):
        p = self.p
        srho, srhou, srhoE = physics.get_state_slices()
        gamma = physics.thermo.gamma

        Uq = np.zeros([x.shape[0], x.shape[1], physics.NUM_STATE_VARS])

        rho = 1.0 + 0.1*np.sin(2.*np.pi*x)
        rhou = rho*1.0
        rhoE = p/(gamma - 1.) + 0.5*rhou**2/rho

        Uq[:, :, srho] = rho
        Uq[:, :, srhou] = rhou
        Uq[:, :, srhoE] = rhoE

        return Uq # [ne, nq, ns]


class RiemannProblem(FcnBase):
    '''
    Riemann problem. Exact solution included (with time dependence),
    obtained using the method of characteristics. Detailed derivation not
    discussed here. Region 1 is to the right of the shock, region 2 between
    the shock and the contact discontinuity, region 3 is between the contact
    discontinuity and the expansion fan, and region 4 is to the left of the
    expansion fan.

    Attributes:
    -----------
    rhoL: float
        left density
    uL: float
        left velocity
    pL: float
        left pressure
    rhoR: float
        right density
    uR: float
        right velocity
    pR: float
        right pressure
    xd: float
        location of initial discontinuity
    '''
    def __init__(self, rhoL=1., uL=0., pL=1., rhoR=0.125, uR=0., pR=0.1,
                xd=0.):
        '''
        This method initializes the attributes.

        Parameters
        ----------
            rhoL: left density
            uL: left velocity
            pL: left pressure
            rhoR: right density
            uR: right velocity
            pR: right pressure
            xd: location of initial discontinuity

        Returns
        -------
            self: attributes initialized

        Notes:
        ------
            Default values set up for Sod problem.
        '''
        self.rhoL = rhoL
        self.uL = uL
        self.pL = pL
        self.rhoR = rhoR
        self.uR = uR
        self.pR = pR
        self.xd = xd

    def get_state(self, physics, x, t):
        ''' Unpack '''
        xd = self.xd
        srho, srhou, srhoE = physics.get_state_slices()

        rho4 = self.rhoL; p4 = self.pL; u4 = self.uL
        rho1 = self.rhoR; p1 = self.pR; u1 = self.uR

        # Set the thermodynamic state in region 1
        Yi = physics.thermo.default_Y[None, None, :]
        rhoi_tmp = rho1 * Yi
        p_tmp = np.array([p1])[None, None, :]
        physics.thermo.set_state_from_rhoi_p(rhoi_tmp, p_tmp)
        gamma = np.array(physics.thermo.gamma).flatten()[0]

        # Speeds of sound in regions 1 and 4
        c4 = np.sqrt(gamma*p4/rho4)
        c1 = np.sqrt(gamma*p1/rho1)

        def F(y):
            # Nonlinear equation to get y = p2/p1
            F = y * (1. + (gamma-1.)/(2.*c4) * (u4 - u1 - c1/gamma*(y-1.)/ \
                    np.sqrt((gamma+1.)/(2.*gamma)*(y-1.) + 1)))**(-2. \
                    *gamma/(gamma-1)) - p4/p1
            return F

        y0 = 0.5*p4/p1 # initial guess
        Y = fsolve(F, y0)

        ''' Region 2 '''
        # Pressure
        p2 = Y*p1
        # Velocity
        u2 = u1 + c1/gamma*(p2/p1-1)/np.sqrt((gamma+1)/(2*gamma)*(p2/p1-1) \
                + 1)
        # Speed of sound
        num = (gamma+1)/(gamma-1) + p2/p1
        den = 1 + (gamma+1)/(gamma-1)*(p2/p1)
        c2 = c1*np.sqrt(p2/p1*num/den)
        # Shock speed
        V = u1 + c1*np.sqrt((gamma+1)/(2*gamma)*(p2/p1-1) + 1)
        # Density
        rho2 = gamma*p2/c2**2

        ''' Region 3 '''
        # Pressure
        p3 = p2
        # Velocity
        u3 = u2
        # Speed of sound
        c3 = (gamma-1)/2*(u4-u3+2/(gamma-1)*c4)
        # Density
        rho3 = gamma*p3/c3**2

        # Expansion fan
        xe1 = (u4-c4)*t + xd; # "start" of expansion fan
        xe2 = (t*((gamma+1)/2*u3 - (gamma-1)/2*u4 - c4)+xd) # end

        # Location of shock
        xs = V*t + xd
        # Location of contact
        xc = u2*t + xd

        u = np.zeros_like(x); p = np.zeros_like(x); rho = np.zeros_like(x);

        for i in range(x.shape[0]):
            for j in range(x.shape[1]):
                if x[i,j] <= xe1:
                    # Left of expansion fan (region 4)
                    u[i,j] = u4; p[i,j] = p4; rho[i,j] = rho4
                elif x[i,j] > xe1 and x[i,j] <= xe2:
                    # Expansion fan
                    u[i,j] = (2/(gamma+1)*((x[i,j]-xd)/t
                            + (gamma-1)/2*u4 + c4))
                    c = u[i,j] - (x[i,j]-xd)/t
                    p[i,j] = p4*(c/c4)**(2*gamma/(gamma-1))
                    rho[i,j] = gamma*p[i,j]/c**2
                elif x[i,j] > xe2 and x[i,j] <= xc:
                    # Between expansion fan and and contact discontinuity
                    # (region 3)
                    u[i,j] = u3; p[i,j] = p3; rho[i,j] = rho3
                elif x[i,j] > xc and x[i,j] <= xs:
                    # Between the contact discontinuity and the shock
                    # (region 2)
                    u[i,j] = u2; p[i,j] = p2; rho[i,j] = rho2
                else:
                    # Right of the shock (region 1)
                    u[i,j] = u1; p[i,j] = p1; rho[i,j] = rho1

        rhoi = rho*Yi
        physics.thermo.set_state_from_rhoi_p(rhoi, p)

        Uq = np.zeros([x.shape[0], x.shape[1], physics.NUM_STATE_VARS])
        Uq[:, :, srho] = rhoi
        Uq[:, :, srhou] = rho*u
        Uq[:, :, srhoE] = rho*physics.thermo.e + 0.5*rho*u*u

        return Uq # [ne, nq, ns]


class TaylorGreenVortex(FcnBase):
    '''
    2D steady-state Taylor-Green vortex problem. Source term required to
    account for incompressibility and ensure steady state. Reference:
        [1] C. Wang, "Reconstructed discontinous Galerkin method for the
        compressible Navier-Stokes equations in arbitrary Langrangian and
        Eulerian formulation", PhD Thesis, North Carolina State University,
        2017.
    '''
    def get_state(self, physics, x, t):
        # Unpack
        Uq = np.zeros([x.shape[0], x.shape[1], physics.NUM_STATE_VARS])
        gamma = physics.thermo.gamma
        Rg = physics.thermo.R

        srho, srhou, srhoE = physics.get_state_slices()

        # State
        rho = 1.
        u = np.sin(np.pi*x[:, :, 0])*np.cos(np.pi*x[:, :, 1])
        v = -np.cos(np.pi*x[:, :, 0])*np.sin(np.pi*x[:, :, 1])
        p = 0.25*(np.cos(2.*np.pi*x[:, :, 0]) + np.cos(2*np.pi*x[:, :, 1]))\
                + 1.
        E = p/(rho*(gamma - 1.)) + 0.5*(u**2. + v**2.)

        # Store
        Uq[:, :, srho] = rho
        Uq[:, :, srhou] = np.stack([rho*u, rho*v], axis=2)
        Uq[:, :, srhoE] = (rho*E)[..., None]

        return Uq # [ne, nq, ns]

class ShuOsherProblem(FcnBase):
    '''
    This test case is used to show the advantages of higher-order methods.
    The case is defined with a Mach 3 shock interacting with a density wave.
    A reference solution is obtained by running a P2 simulation with a large
    element count (~12000).

    It can be found in the following reference:

        [1] Zhong, X., and Shu, C.-W., “A simple weighted essentially
            nonoscillatory limiter for Runge-Kutta discontinuous Galerkin
            methods,” JCP, Vol. 232, No. 1, 2013.

    Attributes:
    -----------
    xshock: float
        initial location of shock
    '''
    def __init__(self, xshock=-4.):
        '''
        This method initializes the attributes.

        Parameters
        ----------
            xshock: initial location of shock

        Returns
        -------
            self: attributes initialized
        '''
        self.xshock = xshock

    def get_state(self, physics, x, t):
        # Unpack
        xshock = self.xshock

        srho, srhou, srhoE = physics.get_state_slices()

        gamma = physics.thermo.gamma

        ''' Pre-shock state '''
        rhoL = 3.857143
        pL = 10.333333
        uL = 2.629369

        ''' Post-shock state '''
        rho_sin = 1. + 0.2 * np.sin(5.*x)
        uR = 0.
        pR = 1.

        ''' Fill state '''
        Uq = np.zeros([x.shape[0], x.shape[1], physics.NUM_STATE_VARS])

        for elem_ID in range(Uq.shape[0]):
            ileft = (x[elem_ID] < xshock).reshape(-1)
            iright = (x[elem_ID] >= xshock).reshape(-1)
            rhoR = rho_sin[elem_ID, iright]
            # Density
            Uq[elem_ID, iright, srho] = rhoR
            Uq[elem_ID, ileft, srho] = rhoL
            # Momentum
            Uq[elem_ID, iright, srhou] = rhoR*uR
            Uq[elem_ID, ileft, srhou] = rhoL*uL
            # Energy
            Uq[elem_ID, iright, srhoE] = pR/(gamma - 1.) + 0.5*rhoR*uR*uR
            Uq[elem_ID, ileft, srhoE] = pL/(gamma - 1.) + 0.5*rhoL*uL*uL

        return Uq # [ne, nq, ns]


class GravityRiemann(FcnBase):
    '''
    2D time dependent riemann problem to test the PPL on a low density
    and pressure case. For more details see the following reference:
        [1] X. Zhang, C.-W. Shu, "Positivity-preserving high-order
        discontinuous Galerkin schemes for compressible Euler equations
        with source terms, Journal of Computational Physics 230
        (2011) 1238–1248.
    '''
    def get_state(self, physics, x, t):
        # Unpack
        Uq = np.zeros([x.shape[0], x.shape[1], physics.NUM_STATE_VARS])
        gamma = physics.thermo.gamma
        Rg = physics.thermo.R

        irho, irhou, irhov, irhoE = physics.get_state_indices()

        # State 1
        rhoL = 7.
        uL = -1.
        pL = .2

        # State 2
        rhoR = 7.
        uR = 1.
        pR = .2

        for elem_ID in range(Uq.shape[0]):
            ileft = (x[elem_ID, :, 0] <= 1.).reshape(-1)
            iright = (x[elem_ID, :, 0] > 1.).reshape(-1)
            # Density
            Uq[elem_ID, ileft, irho] = rhoL
            Uq[elem_ID, iright, irho] = rhoR
            # XMomentum
            Uq[elem_ID, ileft, irhou] = rhoL*uL
            Uq[elem_ID, iright, irhou] = rhoR*uR
            # YMomentum
            Uq[elem_ID, ileft, irhov] = 0.
            Uq[elem_ID, iright, irhov] = 0.
            # Energy
            Uq[elem_ID, ileft, irhoE] = pL/(gamma - 1.) + 0.5*rhoL*uL*uL
            Uq[elem_ID, iright, irhoE] = pR/(gamma - 1.) + 0.5*rhoR*uR*uR

        return Uq # [ne, nq, ns]


'''
-------------------
Boundary conditions
-------------------
These classes inherit from either the BCWeakRiemann or BCWeakPrescribed
classes. See those parent classes for detailed comments of attributes
and methods. Information specific to the corresponding child classes can be
found below. These classes should correspond to the BCType enum members
above.
'''

class SlipWall(BCWeakPrescribed):
    '''
    This class corresponds to a slip wall. See documentation for more
    details.
    '''
    def get_boundary_state(self, physics, UqI, normals, x, t):
        srhou = physics.get_state_slice("Momentum")

        # Unit normals
        n_hat = normals/np.linalg.norm(normals, axis=2, keepdims=True)

        # Remove momentum contribution in normal direction from boundary
        # state
        rhoveln = np.sum(UqI[:, :, srhou] * n_hat, axis=2, keepdims=True)
        UqB = UqI.copy()
        UqB[:, :, srhou] -= rhoveln * n_hat

        return UqB


class SlipWallRiemann(BCWeakRiemann):
    '''
    This class corresponds to a slip wall. See documentation for more
    details.
    '''
    def get_boundary_state(self, physics, UqI, normals, x, t):
        srhou = physics.get_state_slice("Momentum")

        # Unit normals
        n_hat = normals/np.linalg.norm(normals, axis=2, keepdims=True)

        # Remove momentum contribution in normal direction from boundary
        # state
        rhoveln = np.sum(UqI[:, :, srhou] * n_hat, axis=2, keepdims=True)
        UqB = UqI.copy()
        UqB[:, :, srhou] -= 2.0*rhoveln*n_hat

        return UqB


class PressureOutlet(BCWeakPrescribed):
    '''
    This class corresponds to an outflow boundary condition with static
    pressure prescribed. See documentation for more details.

    Attributes:
    -----------
    p: float
        pressure
    '''
    def __init__(self, p):
        '''
        This method initializes the attributes.

        Parameters
        ----------
            p: pressure

        Returns
        -------
            self: attributes initialized
        '''
        self.p = p

    def get_boundary_state(self, physics, UqI, normals, x, t):
        # Unpack
        srho, srhou, srhoE = physics.get_state_slices()

        # Compute the thermodynamic state
        physics.set_thermo_state(UqI)

        # Pressure
        pB = self.p

        gamma = physics.thermo.gamma

        UqB = UqI.copy()

        # Unit normals
        n_hat = normals/np.linalg.norm(normals, axis=2, keepdims=True)

        # Interior velocity in normal direction
        rhoI = physics.thermo.rho
        velI = physics.velocity
        velnI = np.sum(velI*n_hat, axis=2, keepdims=True)

        if np.any(velnI < 0.):
            print("Incoming flow at outlet")

        # Interior pressure
        pI = physics.thermo.p

        if np.any(pI < 0.):
            raise errors.NotPhysicalError

        # Interior speed of sound
        cI = physics.thermo.c
        JI = velnI + 2.*cI/(gamma - 1.)
        # Interior velocity in tangential direction
        veltI = velI - velnI*n_hat

        # Normal Mach number
        Mn = velnI/cI
        if np.any(Mn >= 1.):
            # If supersonic, then extrapolate interior to exterior
            return UqB

        # Boundary density from interior entropy
        rhoB = rhoI*np.power(pB/pI, 1./gamma)
        UqB[:, :, srho] = rhoB

        # Boundary speed of sound
        cB = np.sqrt(gamma*pB/rhoB)
        # Boundary velocity
        velB = (JI - 2.*cB/(gamma-1.))*n_hat + veltI
        UqB[:, :, srhou] = rhoB*velB

        # Boundary energy
        rhovel2B = rhoB*np.sum(velB**2., axis=2, keepdims=True)
        UqB[:, :, srhoE] = pB/(gamma - 1.) + 0.5*rhovel2B

        return UqB


class AdiabaticWall(BCWeakPrescribed):
    '''
    This class corresponds to a viscous wall with zero heat flux
    (adiabatic). See documentation for more details.
    '''

    def get_boundary_state(self, physics, UqI, normals, x, t):
        UqB = UqI.copy()
        _, srhou, srhoE = physics.get_state_slices()

        # Boundary densities = interior densities
        rhoiI = physics.compute_variable("Densities", UqI)
        if np.any(rhoiI < 0.):
            raise errors.NotPhysicalError("Negative densities at adiabatic wall.")

        # Boundary temperature = interior temperature (q=0)
        TI = physics.compute_variable("Temperature", UqI)
        if np.any(TI < 0.):
            raise errors.NotPhysicalError("Negative temperature at adiabatic wall.")

        # Set the thermodynamic state from the interior densities and temperature
        physics.thermo.set_state_from_rhoi_T(rhoiI, TI)

        # Boundary velocity
        UqB[:, :, srhou] = 0.

        # Boundary energy
        UqB[:, :, srhoE] = physics.thermo.rho * physics.thermo.e

        return UqB


class IsothermalWall(BCWeakPrescribed):
    '''
    This class corresponds to a viscous Isothermal wall. See documentation for more
    details.
    '''
    def __init__(self, Twall, method=0):
        '''
        This method initializes the attributes.

        Inputs:
        -------
            Twall: wall temperature

        Outputs:
        --------
            self: attributes initialized
        '''
        self.Twall = Twall
        self.method = method

    def get_boundary_state(self, physics, UqI, normals, x, t):

        if self.method == 1:
            return self.set_rhoE(physics, UqI, normals, x, t)
        elif self.method == 2:
            return self.set_rho(physics, UqI, normals, x, t)

        return self.set_Y_T_p(physics, UqI, normals, x, t)

    def set_Y_T_p(self, physics, UqI, normals, x, t):
        UqB = UqI.copy()
        srho, srhou, srhoE = physics.get_state_slices()

        # Interior pressure and mass fractions
        pI = physics.compute_variable("Pressure", UqI)
        YI = physics.thermo.Y
        if np.any(pI < 0.):
            raise errors.NotPhysicalError

        # Set the boundary thermodynamic state with the specified wall temperature
        # wall pressure pB = pI
        physics.thermo.set_state_from_Y_T_p(YI, self.Twall, pI)

        # Boundary density
        rhoB = physics.thermo.rho
        UqB[:, :, srho] = rhoB * YI

        # Boundary velocity
        UqB[:, :, srhou] = 0.

        # Boundary energy
        rhoEB = rhoB*physics.thermo.e
        UqB[:, :, srhoE] = rhoEB

        return UqB

    def set_rhoE(self, physics, UqI, normals, x, t):
        UqB = UqI.copy()
        srho, srhou, srhoE = physics.get_state_slices()

        # Interior partial densities
        rhoiI = UqI[:, :, srho]
        YI = rhoiI / rhoiI.sum(axis=2, keepdims=True)
        if np.any(rhoiI < 0.):
            raise errors.NotPhysicalError

        # Set the boundary thermodynamic state with the specified wall temperature
        physics.thermo.set_state_from_rhoi_T(rhoiI, self.Twall)

        # Boundary density from boundary internal energy (rhoE = rhoe)
        rhoEB = UqB[:, :, srhoE]
        eB = physics.thermo.e
        UqB[:, :, srho] = (rhoEB / eB) * YI

        # Boundary velocity
        UqB[:, :, srhou] = 0.

        return UqB

    def set_rho(self, physics, UqI, normals, x, t):
        UqB = UqI.copy()
        srho, srhou, srhoE = physics.get_state_slices()

        # Interior partial densities
        rhoiI = UqI[:, :, srho]
        rhoB = rhoiI.sum(axis=2, keepdims=True)
        if np.any(rhoiI < 0.):
            raise errors.NotPhysicalError

        # Set the boundary thermodynamic state with the specified wall temperature
        physics.thermo.set_state_from_rhoi_T(rhoiI, self.Twall)

        # Boundary energy from boundary internal energy (rhoE = rhoe)
        eB = physics.thermo.e
        UqB[:, :, srhoE] = rhoB*eB

        # Boundary velocity
        UqB[:, :, srhou] = 0.

        return UqB


class IsothermalWallRiemann(BCWeakRiemann):
    '''
    This class corresponds to a viscous Isothermal wall. See documentation for more
    details.
    '''
    def __init__(self, Twall):
        '''
        This method initializes the attributes.

        Inputs:
        -------
            Twall: wall temperature

        Outputs:
        --------
            self: attributes initialized
        '''
        self.Twall = Twall

    def get_boundary_state(self, physics, UqI, normals, x, t):
        UqB = UqI.copy()
        srho, srhou, srhoE = physics.get_state_slices()

        # Interior partial densities
        rhoiI = UqI[:, :, srho]
        rhoB = rhoiI.sum(axis=2, keepdims=True)
        if np.any(rhoiI < 0.):
            raise errors.NotPhysicalError

        # Set the boundary thermodynamic state with the specified wall temperature
        physics.thermo.set_state_from_rhoi_T(rhoiI, self.Twall)

        # Flip the boundary velocity
        rhouB = UqI[:, :, srhou]
        UqB[:, :, srhou] = -rhouB

        # Boundary energy
        rhoEB = rhoB*physics.thermo.e + 0.5*(rhouB*rhouB).sum(axis=2, keepdims=True)/rhoB
        UqB[:, :, srhoE] = rhoEB

        return UqB


'''
---------------------
Source term functions
---------------------
These classes inherit from the SourceBase class. See SourceBase for detailed
comments of attributes and methods. Information specific to the
corresponding child classes can be found below. These classes should
correspond to the SourceType enum members above.
'''

class StiffFriction(SourceBase):
    '''
    Stiff source term (1D) of the form:
    S = [0, nu*rho*u, nu*rho*u^2]

    Attributes:
    -----------
    nu: float
        stiffness parameter
    '''
    def __init__(self, nu=-1, **kwargs):
        super().__init__(kwargs)
        '''
        This method initializes the attributes.

        Parameters
        ----------
            nu: source term parameter

        Returns
        -------
            self: attributes initialized
        '''
        self.nu = nu

    def get_source(self, physics, Uq, x, t):
        nu = self.nu

        irho, irhou, irhoE = physics.get_state_indices()

        S = np.zeros_like(Uq)

        eps = general.eps
        S[:, :, irho] = 0.0
        S[:, :, irhou] = nu*(Uq[:, :, irhou])
        S[:, :, irhoE] = nu*((Uq[:, :, irhou])**2/(eps + Uq[:, :, irho]))

        return S

    def get_jacobian(self, physics, Uq, x, t):
        nu = self.nu

        irho, irhou, irhoE = physics.get_state_indices()

        jac = np.zeros([Uq.shape[0], Uq.shape[1], Uq.shape[-1], Uq.shape[-1]])
        vel = Uq[:, :, 1]/(general.eps + Uq[:, :, 0])

        jac[:, :, irhou, irhou] = nu
        jac[:, :, irhoE, irho] = -nu*vel**2
        jac[:, :, irhoE, irhou] = 2.0*nu*vel

        return jac


class TaylorGreenSource(SourceBase):
    '''
    Source term for 2D Taylor-Green vortex (see above). Reference:
        [1] C. Wang, "Reconstructed discontinous Galerkin method for the
        compressible Navier-Stokes equations in arbitrary Langrangian and
        Eulerian formulation", PhD Thesis, North Carolina State University,
        2017.
    '''
    def get_source(self, physics, Uq, x, t):
        gamma = physics.thermo.gamma

        _, _, irhoE = physics.get_state_indices()

        S = np.zeros_like(Uq)

        S[:, :, irhoE] = np.pi/(4.*(gamma - 1.))*(np.cos(3.*np.pi*x[:, :, 0])*
                np.cos(np.pi*x[:, :, 1]) - np.cos(np.pi*x[:, :, 0])*np.cos(3.*
                np.pi*x[:, :, 1]))

        return S


class GravitySource(SourceBase):
    '''
    Gravity source term used with the GravityRiemann problem defined above.
    Adds gravity to the inviscid Euler equations. See the following reference
    for further details:
        [1] X. Zhang, C.-W. Shu, "Positivity-preserving high-order
        discontinuous Galerkin schemes for compressible Euler equations
        with source terms, Journal of Computational Physics 230
        (2011) 1238–1248.
    '''
    def __init__(self, gravity=0., **kwargs):
        super().__init__(kwargs)
        '''
        This method initializes the attributes.

        Parameters
        ----------
            gravity: gravity constant

        Returns
        -------
            self: attributes initialized
        '''
        self.gravity = gravity

    def get_source(self, physics, Uq, x, t):
        # Unpack
        gamma = physics.thermo.gamma
        g = self.gravity

        irho, irhou, irhov, irhoE = physics.get_state_indices()

        S = np.zeros_like(Uq)

        rho = Uq[:, :, irho]
        rhov = Uq[:, :, irhov]

        S[:, :, irhov] = -rho * g
        S[:, :, irhoE] = -rhov * g

        return S # [ne, nq, ns]


'''
------------------------
Numerical flux functions
------------------------
These classes inherit from the ConvNumFluxBase or DiffNumFluxBase class.
See ConvNumFluxBase/DiffNumFluxBase for detailed comments of attributes
and methods. Information specific to the corresponding child classes can
be found below. These classes should correspond to the ConvNumFluxType
or DiffNumFluxType enum members above.
'''


class LaxFriedrichs(ConvNumFluxBase):
    '''
    This class corresponds to the local Lax-Friedrichs flux function.
    This replaces the generalized, less efficient version of
    the Lax-Friedrichs flux found in base.
    '''
    def compute_flux(self, physics, UqL, UqR, normals):
        # Normalize the normal vectors
        n_mag = np.linalg.norm(normals, axis=2, keepdims=True)
        n_hat = normals/n_mag

        # Left flux
        FqL, (uLvec, thermoL) = physics.get_conv_flux_projected(UqL, n_hat)
        aL = thermoL.c + np.linalg.norm(uLvec, axis=2, keepdims=True)

        # Right flux
        FqR, (uRvec, thermoR) = physics.get_conv_flux_projected(UqR, n_hat)
        aR = thermoR.c + np.linalg.norm(uRvec, axis=2, keepdims=True)

        # Jump
        dUq = UqR - UqL

        # Max wave speeds at each point
        idx = aR > aL
        aL[idx] = aR[idx]

        # Put together
        return 0.5 * n_mag * (FqL + FqR - aL*dUq)


class Roe1D(ConvNumFluxBase):
    '''
    Roe numerical flux.

    References
    ----------
    [1] P. L. Roe, "Approximate Riemann solvers, parameter vectors, and
    difference schemes," Journal of Computational Physics,
    43(2):357-372, 1981.
    [2] J. S. Hesthaven, T. Warburton, "Nodal discontinuous Galerkin
    methods: algorithms, analysis, and applications," Springer Science
    & Business Media, 2007.

    Attributes:
    -----------
    UqL: ndarray
        Helper array for left state [nf, nq, ns]
    UqR: ndarray
        Helper array for right state [nf, nq, ns]
    vel: ndarray
        Helper array for velocity [nf, nq, ndims]
    alphas: ndarray
        Helper array: left eigenvectors multipled by dU [nf, nq, ns]
    evals: ndarray
        Helper array for eigenvalues [nf, nq, ns]
    R: ndarray
        Helper array for right eigenvectors [nf, nq, ns, ns]
    '''
    def __init__(self, Uq=None):
        '''
        This method initializes the attributes.

        Parameters
        ----------
        Uq: ndarray
            Values of the state variables (typically at the quadrature
            points) [nf, nq, ns]; used to allocate helper arrays; if None,
            then empty arrays allocated
        '''
        if Uq is not None:
            n, nq, ns = Uq.shape
        else:
            n = nq = ns = 0

        self.UqL = np.zeros_like(Uq)
        self.UqR = np.zeros_like(Uq)
        self.alphas = np.zeros_like(Uq)
        self.evals = np.zeros_like(Uq)
        self.R = np.zeros([n, nq, ns, ns])

    def rotate_coord_sys(self, srhou, Uq, n):
        '''
        This method expresses the momentum vector in the rotated coordinate
        system, which is aligned with the face normal and tangent.

        Parameters
        ----------
        srhou: momentum slice
        Uq: ndarray
            Values of the state variable (typically at the quadrature
            points), with shape `(nf, nq, ns)`.
        n: ndarray
            Normals (typically at the quadrature points), with shape
            `(nf, nq, ndims)`.

        Returns
        -------
        Uq: ndarray
            momentum terms modified
        '''
        Uq[:, :, srhou] *= n

        return Uq

    def undo_rotate_coord_sys(self, srhou, Uq, n):
        '''
        This method expresses the momentum vector in the standard coordinate
        system. It "undoes" the rotation above.

        Parameters
        ----------
        srhou: slice
            Indices of momentum components.
        Uq: ndarray
            Values of the state variable (typically at the quadrature points),
            with shape `(nf, nq, ns)`.
        n: ndarray
            Normal vectors (typically at the quadrature points), with shape
            `(nf, nq, ndims)`.

        Returns
        -------
        Uq: ndarray
            Momentum terms modified.
        '''
        Uq[:, :, srhou] /= n

        return Uq

    def roe_average_state(self, rhoL, rhoR, YL, YR, velL, velR, HL, HR):
        '''
        This method computes the Roe-averaged variables.

        Parameters
        ----------
        rhoL: ndarray
            Left density (typically evaluated at the quadrature points) with
            shape `(nf, nq, 1)`.
        rhoR: ndarray
            Right density (typically evaluated at the quadrature points) with
            shape `(nf, nq, 1)`.
        YL: ndarray
            Left species mass fractions (typically evaluated at the quadrature
            points) with shape `(nf, nq, nsp)`.
        YR: ndarray
            Right species mass fractions (typically evaluated at the quadrature
            points) with shape `(nf, nq, nsp)`.
        velL: ndarray
            Left velocity (typically evaluated at the quadrature points) with
            shape `(nf, nq, ndims)`.
        velR: ndarray
            Right velocity (typically evaluated at the quadrature points) with
            shape `(nf, nq, ndims)`.
        HL: ndarray
            Left total enthalpy (typically evaluated at the quadrature points)
            with shape `(nf, nq, 1)`.
        HR: ndarray
            Right total enthalpy (typically evaluated at the quadrature points)
            with shape `(nf, nq, 1)`.

        Returns
        -------
        rhoRoe: ndarray
            Roe-averaged density with shape `(nf, nq, 1)`.
        YRoe: ndarray
            Roe-averaged species mass fractions with shape `(nf, nq, nsp)`.
        velRoe: ndarray
            Roe-averaged velocity with shape `(nf, nq, ndims)`.
        HRoe: ndarray
            Roe-averaged total enthalpy with shape `(nf, nq, 1)`.
        '''
        rhoL_sqrt = np.sqrt(rhoL)
        rhoR_sqrt = np.sqrt(rhoR)
        denom = 1.0 / (rhoL_sqrt + rhoR_sqrt)

        YRoe = (rhoL_sqrt*YL + rhoR_sqrt*YR)*denom
        velRoe = (rhoL_sqrt*velL + rhoR_sqrt*velR)*denom
        rhoRoe = rhoL_sqrt*rhoR_sqrt
        HRoe = (rhoL_sqrt*HL + rhoR_sqrt*HR)*denom

        return rhoRoe, YRoe, velRoe, HRoe

    def get_differences(self, rhoL, rhoR, YL, YR, velL, velR, pL, pR):
        '''
        This method computes velocity, density, and pressure jumps.

        Parameters
        ----------
        rhoL: ndarray
            Left density (typically evaluated at the quadrature points) with
            shape `(nf, nq, 1)`.
        rhoR: ndarray
            Right density (typically evaluated at the quadrature points) with
            shape `(nf, nq, 1)`.
        YL: ndarray
            Left species mass fractions (typically evaluated at the quadrature
            points) with shape `(nf, nq, nsp)`.
        YR: ndarray
            Right species mass fractions (typically evaluated at the quadrature
            points) with shape `(nf, nq, nsp)`.
        velL: ndarray
            Left velocity (typically evaluated at the quadrature points) with
            shape `(nf, nq, ndims)`.
        velR: ndarray
            Right velocity (typically evaluated at the quadrature points) with
            shape `(nf, nq, ndims)`.
        pL: ndarray
            Left pressure (typically evaluated at the quadrature points) with
            shape `(nf, nq, 1)`.
        pR: ndarray
            Right pressure (typically evaluated at the quadrature points) with
            shape `(nf, nq, 1)`.

        Returns
        -------
        drhoY: ndarray
            Jump in species partial densities with shape `(nf, nq, nsp)`.
        dvel: ndarray
            Jump in velocity with shape `(nf, nq, ndims)`.
        dp: ndarray
            Jump in pressure with shape `(nf, nq, 1)`.
        '''
        drhoY = rhoR*YR - rhoL*YL
        dvel = velR - velL
        dp = pR - pL

        return drhoY, dvel, dp

    def get_alphas(self, c, c2, dp, dvel, drho, rhoRoe):
        '''
        This method computes alpha_i = ith left eigenvector * dU.

        Parameters
        ----------
        c: speed of sound [nf, nq, 1]
        c2: speed of sound squared [nf, nq, 1]
        dp: pressure jump [nf, nq, 1]
        dvel: velocity jump [nf, nq, ndims]
        drho: density jump [nf, nq, 1]
        rhoRoe: Roe-averaged density [nf, nq, 1]

        Returns
        -------
        alphas: left eigenvectors multipled by dU [nf, nq, ns]
        '''
        alphas = self.alphas

        alphas[:, :, [0]] = 0.5/c2*(dp - c*rhoRoe*dvel[:, :, [0]])
        alphas[:, :, 1:-1] = drho - dp/c2
        alphas[:, :, [-1]] = 0.5/c2*(dp + c*rhoRoe*dvel[:, :, [0]])

        return alphas

    def get_eigenvalues(self, velRoe, c):
        '''
        This method computes the eigenvalues.

        Parameters
        ----------
        velRoe: ndarray
            Roe-averaged velocity with shape `(nf, nq, ndims)`.
        c: ndarray
            Speed of sound with shape `(nf, nq, 1)`.

        Returns
        -------
        evals: ndarray
            Array of Eigenvalues with shape `(nf, nq, ns)`.
        '''
        evals = self.evals

        evals[:, :, [0]] = velRoe[:, :, [0]] - c
        evals[:, :, 1:-1] = velRoe[:, :, [0]]
        evals[:, :, [-1]] = velRoe[:, :, [0]] + c

        return evals

    def get_right_eigenvectors(self, c, evals, velRoe, HRoe):
        '''
        This method computes the right eigenvectors.

        Parameters
        ----------
        c: ndarray
            Speed of sound with shape `(nf, nq, 1)`.
        evals: ndarray
            Array of Eigenvalues with shape `(nf, nq, ns)`.
        velRoe: ndarray
            Roe-averaged velocity with shape `(nf, nq, ndims)`.
        HRoe: ndarray
            Roe-averaged total enthalpy with shape `(nf, nq, 1)`.

        Returns
        -------
        R: ndarray
            Right eigenvectors with shape `(nf, nq, ns, ns)`.
        '''
        R = self.R

        # first row
        R[:, :, 0, 0:2] = 1.
        R[:, :, 0, -1] = 1.
        # second row
        R[:, :, 1, 0] = evals[:, :, 0]; R[:, :, 1, 1] = velRoe[:, :, 0]
        R[:, :, 1, -1] = evals[:, :, -1]
        # last row
        R[:, :, -1, 0:1] = HRoe - velRoe[:, :, 0:1]*c
        R[:, :, -1, 1:2] = 0.5*np.sum(velRoe*velRoe, axis=2, keepdims=True)
        R[:, :, -1, -1:] = HRoe + velRoe[:, :, 0:1]*c

        return R

    def compute_flux(self, physics, UqL_std, UqR_std, normals):
        # Reshape arrays
        n, nq, ns = UqL_std.shape
        ndims = physics.NDIMS
        self.vel = np.zeros([n, nq, ndims])
        self.alphas = np.zeros_like(UqL_std)
        self.evals = np.zeros_like(UqL_std)
        self.R = np.zeros([n, nq, ns, ns])

        # Unpack
        srhou = physics.get_state_slice("Momentum")

        # Unit normals
        n_mag = np.linalg.norm(normals, axis=2, keepdims=True)
        n_hat = normals/n_mag

        # Copy values from standard coordinate system before rotating
        UqL = UqL_std.copy()
        UqR = UqR_std.copy()

        # Rotated coordinate system
        UqL = self.rotate_coord_sys(srhou, UqL, n_hat)
        UqR = self.rotate_coord_sys(srhou, UqR, n_hat)

        # Get left state
        physics.set_thermo_state(UqL)
        gamma = physics.thermo.gamma
        rhoL = physics.thermo.rho
        YL = physics.thermo.Y
        velL = physics.velocity
        pL = physics.thermo.p
        # HL = physics.thermo.h + physics.kinetic_energy / rhoL
        HL = physics.compute_variable("TotalEnthalpy", UqL)
        if np.any(rhoL <= 0.):
            # Non-physical state
            raise errors.NotPhysicalError("rhoL is negative")

        # Get right state
        physics.set_thermo_state(UqR)
        rhoR = physics.thermo.rho
        YR = physics.thermo.Y
        velR = physics.velocity
        pR = physics.thermo.p
        # HR = physics.thermo.h + physics.kinetic_energy / rhoR
        HR = physics.compute_variable("TotalEnthalpy", UqR)
        if np.any(rhoR <= 0.):
            # Non-physical state
            raise errors.NotPhysicalError("rhoR is negative")

        # Roe-averaged state
        rhoRoe, YRoe, velRoe, HRoe = self.roe_average_state(rhoL, rhoR, YL, YR, velL, velR, HL, HR)

        # Speed of sound from Roe-averaged state
        c2 = (gamma - 1.)*(HRoe - 0.5*np.sum(velRoe*velRoe, axis=2, keepdims=True))
        if np.any(c2 <= 0.):
            # Non-physical state
            error = 'NaN' if np.any(np.isnan(c2)) else 'negative'
            raise errors.NotPhysicalError("Speed of sound is %s" % error)
        c = np.sqrt(c2)

        # Jumps
        drhoY, dvel, dp = self.get_differences(rhoL, rhoR, YL, YR, velL, velR, pL, pR)
        drho = drhoY.sum(axis=2, keepdims=True)

        # alphas (left eigenvectors multiplied by dU)
        alphas = self.get_alphas(c, c2, dp, dvel, drho, rhoRoe)

        # Eigenvalues
        evals = self.get_eigenvalues(velRoe, c)

        # Entropy fix (currently commented as we have yet to decide
        # if this is needed long term)
        # eps = np.zeros_like(evals)
        # eps[:, :, :] = (1e-2 * c)
        # fix = np.argwhere(np.logical_and(evals < eps, evals > -eps))
        # fix_shape = fix[:, 0], fix[:, 1], fix[:, 2]
        # evals[fix_shape] = 0.5 * (eps[fix_shape] + evals[fix_shape]* \
        # 	evals[fix_shape] / eps[fix_shape])

        # Right eigenvector matrix
        R = self.get_right_eigenvectors(c, evals, velRoe, HRoe)

        # Form flux Jacobian matrix multiplied by dU
        FRoe = np.einsum('ijkl, ijl -> ijk', R, np.abs(evals)*alphas)

        # Undo rotation
        FRoe = self.undo_rotate_coord_sys(srhou, FRoe, n_hat)

        # Left flux
        FL, _ = physics.get_conv_flux_projected(UqL_std, n_hat)

        # Right flux
        FR, _ = physics.get_conv_flux_projected(UqR_std, n_hat)

        return .5*n_mag*(FL + FR - FRoe) # [nf, nq, ns]


class Roe2D(Roe1D):
    '''
    2D Roe numerical flux. This class inherits from the Roe1D class.
    See Roe1D for detailed comments on the attributes and methods.
    In this class, several methods are updated to account for the extra
    dimension.
    '''
    def rotate_coord_sys(self, srhou, Uq, n):
        vel = self.vel
        vel[:] = Uq[:, :, srhou]

        vel[:, :, 0] = np.sum(Uq[:, :, srhou]*n, axis=2)
        vel[:, :, 1] = np.sum(Uq[:, :, srhou]*n[:, :, ::-1]*np.array([[-1.,
                1.]]), axis=2)

        Uq[:, :, srhou] = vel

        return Uq

    def undo_rotate_coord_sys(self, srhou, Uq, n):
        vel = self.vel
        vel[:] = Uq[:, :, srhou]

        vel[:, :, 0] = np.sum(Uq[:, :, srhou]*n*np.array([[1., -1.]]), axis=2)
        vel[:, :, 1] = np.sum(Uq[:, :, srhou]*n[:, :, ::-1], axis=2)

        Uq[:, :, srhou] = vel

        return Uq

    def get_alphas(self, c, c2, dp, dvel, drho, rhoRoe):
        alphas = self.alphas

        alphas = super().get_alphas(c, c2, dp, dvel, drho, rhoRoe)

        alphas[:, :, 2:3] = rhoRoe*dvel[:, :, -1:]

        return alphas

    def get_eigenvalues(self, velRoe, c):
        evals = self.evals

        evals = super().get_eigenvalues(velRoe, c)

        evals[:, :, 2:3] = velRoe[:, :, 0:1]

        return evals

    def get_right_eigenvectors(self, c, evals, velRoe, HRoe):
        R = self.R

        R = super().get_right_eigenvectors(c, evals, velRoe, HRoe)

        i = 2

        # First row
        R[:, :, 0, i] = 0.
        #  Second row
        R[:, :, 1, i] = 0.
        #  Last (fourth) row
        R[:, :, -1, i] = velRoe[:, :, -1]
        #  Third row
        R[:, :, i, 0] = velRoe[:, :, -1];  R[:, :, i, 1] = velRoe[:, :, -1]
        R[:, :, i, -1] = velRoe[:, :, -1]; R[:, :, i, i] = 1.

        return R


class HLLC(ConvNumFluxBase):
    '''
    This class implements the modified Harten-Lax-van Leer (HLL) scheme.
    '''
    def get_wave_speeds(self, rhoL, rhoR, aL, aR, pL, pR, uL, uR, gL, gR):
        estimators = [
            self.get_wave_speeds_roe,
            self.get_wave_speeds_pvrs,
            ]

        # SL, SR = 1e30, -1e30
        SL, SR = uL-aL, uR+aR
        for estimator in estimators:
            SLtemp, SRtemp = estimator(rhoL, rhoR, aL, aR, pL, pR, uL, uR, gL, gR)
            SL = np.minimum(SL, SLtemp)
            SR = np.maximum(SR, SRtemp)

        return SL, SR

    def get_wave_speeds_roe(self, rhoL, rhoR, aL, aR, pL, pR, uL, uR, gL, gR):
        a2L = aL*aL
        a2R = aR*aR
        rhoL_sqrt = np.sqrt(rhoL)
        rhoR_sqrt = np.sqrt(rhoR)
        denom = 1.0 / (rhoL_sqrt + rhoR_sqrt)

        uRoe = (rhoL_sqrt*uL + rhoR_sqrt*uR)*denom
        aRoe = np.sqrt(
            (rhoL_sqrt*a2L + rhoR_sqrt*a2R)*denom +
            0.5*(rhoL_sqrt*rhoR_sqrt*(uR-uL)**2)*denom**2
            )

        SL = uRoe - aRoe
        SR = uRoe + aRoe

        return SL, SR

    def get_wave_speeds_pvrs(self, rhoL, rhoR, aL, aR, pL, pR, uL, uR, gL, gR):
        # Primitive-Variable Riemann Solver (PVRS):
        rho_avg = 0.5*(rhoL + rhoR)
        a_avg = 0.5*(aL + aR)
        p_pvrs = 0.5*(pL + pR - (uR-uL)*rho_avg*a_avg)

        # Left wave speed
        qL = np.ones(pL.shape)
        idx = np.where(p_pvrs > pL)[:2]
        g = gL[*idx, :] if isinstance(gL, np.ndarray) else gL
        qL[*idx, :] = np.sqrt(1.0 + (g+1)/(2.0*g) * (p_pvrs[*idx, :]/pL[*idx, :] - 1.0))
        SL = uL - aL*qL

        # Right wave speed
        qR = np.ones(pL.shape)
        idx = np.where(p_pvrs > pR)[:2]
        g = gR[*idx, :] if isinstance(gR, np.ndarray) else gR
        qR[*idx, :] = np.sqrt(1.0 + (g+1)/(2.0*g) * (p_pvrs[*idx, :]/pR[*idx, :] - 1.0))
        SR = uR + aR*qR

        return SL, SR

    def compute_flux(self, physics, UqL, UqR, normals):
        # Normalize the normal vectors
        n_mag = np.linalg.norm(normals, axis=2, keepdims=True)
        n_hat = normals/n_mag

        # Left flux
        FqL, (uLvec, thermoL) = physics.get_conv_flux_projected(UqL, n_hat)
        uL = (uLvec*n_hat).sum(axis=2, keepdims=True)
        u2L = (uLvec*uLvec).sum(axis=2, keepdims=True)
        rhoL = thermoL.rho
        pL = thermoL.p
        aL = thermoL.c
        gL = thermoL.gamma
        YL = thermoL.Y
        eL = thermoL.e

        # Right flux
        FqR, (uRvec, thermoR) = physics.get_conv_flux_projected(UqR, n_hat)
        uR = (uRvec*n_hat).sum(axis=2, keepdims=True)
        u2R = (uRvec*uRvec).sum(axis=2, keepdims=True)
        rhoR = thermoR.rho
        pR = thermoR.p
        aR = thermoR.c
        gR = thermoR.gamma
        YR = thermoR.Y
        eR = thermoR.e

        # Estimate the wave speeds
        SL, SR = self.get_wave_speeds(rhoL, rhoR, aL, aR, pL, pR, uL, uR, gL, gR)

        # Initialize flux to left flux
        F = FqL

        # Set points where SR <= 0 to right flux
        idx = np.where(SR <= 0.0)[:2]
        F[*idx, :] = FqR[*idx, :]

        # Downselect to points where SL < 0 < SR
        idx = np.where(np.logical_and(SL < 0, SR > 0))[:2]

        # Initialize with left values
        Sk = SL[*idx, :]
        pk = pL[*idx, :]
        rhok = rhoL[*idx, :]
        uk = uL[*idx, :]
        u2k = u2L[*idx, :]
        Yk = YL[*idx, :]
        ek = eL[*idx, :]
        vk = uLvec[*idx, :]
        Uk = UqL[*idx, :]

        # Shear wave speed
        alphaL = alphak = rhok*(Sk-uk)
        alphaR = rhoR[*idx, :]*(SR[*idx, :]-uR[*idx, :])
        Sstar = (pR[*idx, :] - pk + uk*alphaL - uR[*idx, :]*alphaR) / (alphaL - alphaR)

        # Overwrite values with right side where S* <= 0
        idxR = np.where(Sstar < 0.0)[0]
        idxR_main = tuple([subidx[idxR] for subidx in idx])
        Sk[idxR, :] = SR[*idxR_main, :]
        pk[idxR, :] = pR[*idxR_main, :]
        rhok[idxR, :] = rhoR[*idxR_main, :]
        uk[idxR, :] = uR[*idxR_main, :]
        u2k[idxR, :] = u2R[*idxR_main, :]
        Yk[idxR, :] = YR[*idxR_main, :]
        ek[idxR, :] = eR[*idxR_main, :]
        vk[idxR, :] = uRvec[*idxR_main, :]
        Uk[idxR, :] = UqR[*idxR_main, :]

        F[*idxR_main, :] = FqR[*idxR_main, :]
        alphak[idxR, :] = alphaR[idxR, :]

        # Combine to get overall flux
        rhokstar = alphak / (Sk - Sstar)
        C = (Sstar-uk)*(Sstar + pk/alphak)
        vk += n_hat[*idx, :]*(Sstar - (vk*n_hat[*idx, :]).sum(axis=1, keepdims=True))
        Ustar = rhokstar*np.concatenate([Yk, vk, ek+0.5*u2k+C], axis=-1)
        dF = Sk*(Ustar - Uk)

        F[*idx, :] += dF

        return n_mag*F
