import code

import processing.post as post
import processing.plot as plot
import processing.readwritedatafiles as readwritedatafiles

### Postprocess
fname = "Data_LF_cfl0p1.pkl"
solver1 = readwritedatafiles.read_data_file(fname)

fname = "Data_Smooth_LF_w0p01.pkl"
solver2 = readwritedatafiles.read_data_file(fname)

fname = "Data_Smooth_LF_w0p05.pkl"
solver3 = readwritedatafiles.read_data_file(fname)

fname = "Data_Smooth_LF_w0p1.pkl"
solver4 = readwritedatafiles.read_data_file(fname)

fname = "Data_Smooth_LF_w0p5.pkl"
solver5 = readwritedatafiles.read_data_file(fname)
# Unpack
mesh1 = solver1.mesh
physics1 = solver1.EqnSet
mesh2 = solver2.mesh
physics2 = solver2.EqnSet
mesh3 = solver3.mesh
physics3 = solver3.EqnSet
mesh4 = solver4.mesh
physics4 = solver4.EqnSet
mesh5 = solver5.mesh
physics5 = solver5.EqnSet

### Postprocess
# fname = "Data_Final.pkl"
# solver2 = readwritedatafiles.read_data_file(fname)
# # print('Solution Final Time:', solver.Time)

# # Unpack
# mesh2 = solver2.mesh
# physics2 = solver2.EqnSet

# Error
# TotErr,_ = post.L2_error(mesh, physics, solver, "Density")
# Plot
plot.PreparePlot()

skip = 7

# Plot Density of all cases
plot.plot_solution(mesh1, physics1, solver1, "Density", plot_numerical=True, plot_exact=False, plot_IC=False, create_new_figure=True, 
			ylabel=None, fmt='--', legend_label="Sharp", equidistant_pts=True, 
			include_mesh=False, regular_2D=False, equal_AR=False, skip=skip)
# plot.plot_solution(mesh1, physics2, solver2, "Density", plot_numerical=True, plot_exact=False, plot_IC=False, create_new_figure=False, 
# 			ylabel=None, fmt='g', legend_label="$w=0.01$", equidistant_pts=True, 
# 			include_mesh=False, regular_2D=False, equal_AR=False, skip=skip)
plot.plot_solution(mesh1, physics3, solver3, "Density", plot_numerical=True, plot_exact=False, plot_IC=False, create_new_figure=False, 
			ylabel=None, fmt='bx', legend_label="$w=0.05$", equidistant_pts=True, 
			include_mesh=False, regular_2D=False, equal_AR=False, skip=skip)
# plot.plot_solution(mesh1, physics4, solver4, "Density", plot_numerical=True, plot_exact=False, plot_IC=False, create_new_figure=False, 
# 			ylabel=None, fmt='c', legend_label="$w=0.1$", equidistant_pts=True, 
# 			include_mesh=False, regular_2D=False, equal_AR=False, skip=skip)
# plot.plot_solution(mesh1, physics5, solver5, "Density", plot_numerical=True, plot_exact=False, plot_IC=False, create_new_figure=False, 
# 			ylabel=None, fmt='r', legend_label="$w=0.5$", equidistant_pts=True, 
# 			include_mesh=False, regular_2D=False, equal_AR=False, skip=skip)
plot.SaveFigure(FileName='SodProblem_IC_comparison_Density_1point', FileType='pdf', CropLevel=2)

# Plot Velocity of all cases
plot.plot_solution(mesh1, physics1, solver1, "Velocity", plot_numerical=True, plot_exact=False, plot_IC=False, create_new_figure=True, 
			ylabel=None, fmt='--', legend_label="Sharp", equidistant_pts=True, 
			include_mesh=False, regular_2D=False, equal_AR=False, skip=skip)
# plot.plot_solution(mesh1, physics2, solver2, "Velocity", plot_numerical=True, plot_exact=False, plot_IC=False, create_new_figure=False, 
			# ylabel=None, fmt='g', legend_label="$w=0.01$", equidistant_pts=True, 
			# include_mesh=False, regular_2D=False, equal_AR=False, skip=skip)
plot.plot_solution(mesh1, physics3, solver3, "Velocity", plot_numerical=True, plot_exact=False, plot_IC=False, create_new_figure=False, 
			ylabel=None, fmt='bx', legend_label="$w=0.05$", equidistant_pts=True, 
			include_mesh=False, regular_2D=False, equal_AR=False, skip=skip)
# plot.plot_solution(mesh1, physics4, solver4, "Velocity", plot_numerical=True, plot_exact=False, plot_IC=False, create_new_figure=False, 
# 			ylabel=None, fmt='c', legend_label="$w=0.1$", equidistant_pts=True, 
# 			include_mesh=False, regular_2D=False, equal_AR=False, skip=skip)
# plot.plot_solution(mesh1, physics5, solver5, "Velocity", plot_numerical=True, plot_exact=False, plot_IC=False, create_new_figure=False, 
# 			ylabel=None, fmt='r', legend_label="$w=0.5$", equidistant_pts=True, 
# 			include_mesh=False, regular_2D=False, equal_AR=False, skip=skip)
plot.SaveFigure(FileName='SodProblem_IC_comparison_Velocity_1point', FileType='pdf', CropLevel=2)

# plot.plot_solution(mesh1, physics1, solver1, "Velocity", plot_numerical=True, plot_exact=False, plot_IC=False, create_new_figure=True, 
# 			ylabel=None, fmt='bo', legend_label="DG", equidistant_pts=True, 
# 			include_mesh=False, regular_2D=False, equal_AR=False)
# plot.plot_solution(mesh1, physics1, solver1, "Density", plot_numerical=True, plot_exact=False, plot_IC=False, create_new_figure=True, 
# 			ylabel=None, fmt='bo', legend_label="DG", equidistant_pts=True, 
# 			include_mesh=False, regular_2D=False, equal_AR=False)
# # plot.plot_solution(mesh2, physics2, solver2, "Velocity", plot_numerical=True, plot_exact=False, plot_IC=False, create_new_figure=True, 
# # 			ylabel=None, fmt='go', legend_label="DG", equidistant_pts=True, 
# # 			include_mesh=False, regular_2D=False, equal_AR=False, skip=7)


# # plot.plot_solution(mesh, physics, solver, "Energy", plot_exact=True, plot_numerical=False, create_new_figure=False, fmt='k-')
# # plot.plot_solution(mesh, physics, solver, "Energy", plot_IC=True, plot_numerical=False, create_new_figure=False, fmt='k--')
# # plot.SaveFigure(FileName='Velocity', FileType='pdf', CropLevel=2)

# plot.plot_solution(mesh1, physics1, solver1, "Pressure", plot_numerical=True, plot_exact=False, plot_IC=False, create_new_figure=True, 
# 			ylabel=None, fmt='bo', legend_label="DG", equidistant_pts=True, 
# 			include_mesh=False, regular_2D=False, equal_AR=False)

# plot.plot_solution(mesh2, physics2, solver2, "Pressure", plot_numerical=True, plot_exact=False, plot_IC=False, create_new_figure=True, 
# 			ylabel=None, fmt='go', legend_label="DG", equidistant_pts=True, 
# 			include_mesh=False, regular_2D=False, equal_AR=False, skip=7)
# plot.plot_solution(mesh, physics, solver, "Pressure", plot_exact=True, plot_numerical=False, create_new_figure=False, fmt='k-')
# plot.plot_solution(mesh, physics, solver, "Pressure", plot_IC=True, plot_numerical=False, create_new_figure=False, fmt='k--')
# plot.SaveFigure(FileName='Pressure', FileType='pdf', CropLevel=2)
# plot.PlotSolution(mesh, physics, solver, "Energy", PlotExact=True, PlotIC=True, legend_label="$p=2$")
# plot.PlotSolution(mesh, physics, solver, "Pressure", create_new_figure=False, legend_label="$p=2$")

# plot.SaveFigure(FileName='SmoothIsentropicFlow', FileType='pdf', CropLevel=2)

plot.ShowPlot()