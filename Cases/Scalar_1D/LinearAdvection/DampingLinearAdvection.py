import sys; sys.path.append('../../../src'); sys.path.append('./src')
import numpy as np
import code
import solver.DG as Solver
import physics.scalar.scalar as Scalar
import meshing.common as MeshCommon
import processing.post as Post
import processing.plot as Plot
import general


### Mesh
Periodic = False
# Uniform mesh
mesh = MeshCommon.mesh_1D(Uniform=True, nElem=16, xmin=-1., xmax=1., Periodic=Periodic)
# Non-uniform mesh
# nElem = 25
# Coords = np.cos(np.linspace(np.pi,0.,nElem+1))
# Coords = MeshCommon.refine_uniform_1D(Coords)
# # Coords = MeshCommon.refine_uniform_1D(Coords)
# mesh = MeshCommon.mesh_1D(Coords=Coords, Periodic=Periodic)


### Solver parameters
EndTime = 0.5
nTimeStep = np.amax([1,int(EndTime/((mesh.Coords[1,0] - mesh.Coords[0,0])*0.1))])
InterpOrder = 2
Params = general.SetSolverParams(InterpOrder=InterpOrder,EndTime=EndTime,nTimeStep=nTimeStep,
								 InterpBasis="LagrangeEqSeg",InterpolateFlux=True)
nu = -3.

### Physics
Velocity = 1.0 
EqnSet = Scalar.ConstAdvScalar1D(Params["InterpOrder"], Params["InterpBasis"], mesh)
EqnSet.set_physical_params(ConstVelocity=Velocity)
EqnSet.set_conv_num_flux("LaxFriedrichs")

EqnSet.set_IC(IC_type="Sine", omega = 2*np.pi)
EqnSet.set_exact(exact_type="DampingSine", omega = 2*np.pi, nu = nu)
EqnSet.set_source(source_type="SimpleSource", nu = nu)




# Boundary conditions
if Velocity >= 0.:
	Inflow = "Left"; Outflow = "Right"
else:
	Inflow = "Right"; Outflow = "Left"
# if not Periodic:
# 	for ibfgrp in range(mesh.nBFaceGroup):
# 		BFG = mesh.BFaceGroups[ibfgrp]
# 		if BFG.Name is Inflow:
# 			EqnSet.set_BC(BC_type="StateAll", fcn_type="DampingSine", omega = 2*np.pi, nu=nu)
# 		elif BFG.Name is Outflow:
# 			EqnSet.set_BC(BC_type="Extrapolate")

if not Periodic:
	EqnSet.set_BC(bname=Inflow, BC_type="StateAll", fcn_type="DampingSine", omega = 2*np.pi, nu=nu)
	EqnSet.set_BC(bname=Outflow, BC_type="Extrapolate")

### Solve
solver = Solver.DG(Params,EqnSet,mesh)
solver.solve()


### Postprocess
# Error
TotErr,_ = Post.L2_error(mesh, EqnSet, solver, "Scalar")
# Plot
# Plot.PreparePlot()
# Plot.PlotSolution(mesh, EqnSet, solver, "Scalar", PlotExact=True, PlotIC=True, Label="u")
# Plot.ShowPlot()


# code.interact(local=locals())
