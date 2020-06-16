import numpy as np
import driver
# import sys; sys.path.append('../../../src'); sys.path.append('./src')
import processing.post as Post

TimeStepping = {
    "StartTime" : 0.,
    "EndTime" : 0.5,
    "nTimeStep" : 40,
    "TimeScheme" : "RK4",
}

Numerics = {
    "InterpOrder" : 2,
    "InterpBasis" : "LagrangeEqSeg",
    "Solver" : "DG",
}

Output = {
    "AutoProcess" : True
}

Mesh = {
    "File" : None,
    "ElementShape" : "Segment",
    "nElem_x" : 16,
    "nElem_y" : 2,
    "xmin" : -1.,
    "xmax" : 1.,
    # "PeriodicBoundariesX" : ["x1", "x2"],
}

Physics = {
    "Type" : "ConstAdvScalar",
    "ConvFlux" : "LaxFriedrichs",
    "ConstVelocity" : 1.,
}

nu = -3.
InitialCondition = {
    "Function" : "DampingSine",
    "omega" : 2*np.pi,
    "nu" : nu,
    "SetAsExact" : True,
}

BoundaryConditions = {
    "Left" : {
	    "Function" : "DampingSine",
	    "omega" : 2*np.pi,
	    "nu" : nu,
    	"BCType" : "FullState",
    },
    "Right" : {
    	"Function" : None,
    	"BCType" : "Extrapolation",
    },
}

SourceTerms = {
	"source1" : {
		"Function" : "SimpleSource",
		"nu" : nu,
	},
}

# solver, EqnSet, mesh = driver.driver(TimeStepping, Numerics, Output, Mesh,
#         Physics, InitialCondition, BoundaryConditions, SourceTerms)


# ### Postprocess
# # Error
# TotErr,_ = Post.L2_error(mesh, EqnSet, solver, "Scalar")