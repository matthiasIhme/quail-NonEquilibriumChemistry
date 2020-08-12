import sys; sys.path.append('../../../src'); sys.path.append('./src')
import numpy as np
import code
import solver.DG as Solver
import physics.euler.euler as Euler
import meshing.common as MeshCommon
import processing.post as Post
import processing.plot as Plot
import general
import meshing.gmsh as MeshGmsh


### Mesh
Periodic = False
# mesh = MeshCommon.mesh_1D(Uniform=True, num_elems=2, xmin=-1., xmax=1., Periodic=Periodic)
mesh = MeshGmsh.import_gmsh_mesh("mesh_v2.msh")


### Solver parameters
EndTime = 0.1
NumTimeSteps = 100
InterpOrder = 5
Params = general.SetSolverParams(InterpOrder=InterpOrder,EndTime=EndTime,NumTimeSteps=NumTimeSteps,
								 InterpBasis="LagrangeSeg",TimeScheme="RK4",InterpolateIC=True)


### Physics
physics = Euler.Euler1D(Params["InterpOrder"], Params["InterpBasis"], mesh)
physics.set_physical_params(GasConstant=1.,SpecificHeatRatio=3.)
physics.set_conv_num_flux("LaxFriedrichs")
# Initial conditions
physics.set_IC(IC_type="SmoothIsentropicFlow", a=0.9)
physics.set_exact(exact_type="SmoothIsentropicFlow", a=0.9)

# Boundary conditions
# if not Periodic:
# 	for ibfgrp in range(mesh.num_boundary_groups):
# 		BFG = mesh.boundary_groups[ibfgrp]
# 		if BFG.Name is "Left":
# 			physics.set_BC(BC_type="StateAll", fcn_type="SmoothIsentropicFlow", a=0.9)
# 		elif BFG.Name is "Right":
# 			physics.set_BC(BC_type="StateAll", fcn_type="SmoothIsentropicFlow", a=0.9)
if not Periodic:
	physics.set_BC(bname="Left", BC_type="StateAll", fcn_type="SmoothIsentropicFlow", a=0.9)
	physics.set_BC(bname="Right", BC_type="StateAll", fcn_type="SmoothIsentropicFlow", a=0.9)

### Solve
solver = Solver.DG(Params,physics,mesh)
solver.solve()


### Postprocess
# Error
TotErr,_ = Post.L2_error(mesh, physics, solver, "Density")
# Plot
# Plot.PreparePlot()
# Plot.PlotSolution(mesh, physics, solver, "Energy", PlotExact=True, Equidistant=True, include_mesh=True, EqualAR=True, show_elem_IDs=True)
# Plot.ShowPlot()


# code.interact(local=locals())