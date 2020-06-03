import numpy as np
from General import *
import Mesh
import code
import Basis
import QuadratureRulesSeg, QuadratureRulesQuad, QuadratureRulesTri


def get_gaussian_quadrature_elem(mesh, basis, order, EqnSet=None, quadData=None):
	'''
	Method: get_gaussian_quadrature_elem
	----------------------------------------
	Determines the quadrature order for the given element based on
	the basis functions, order, and equations.

	INPUTS:
		mesh: mesh object
		basis: polynomial basis function
		order: solution order 
		EqnSet: set of equations to be solved

	OUTPUTS:
		QuadOrder: quadrature order
		QuadChanged: boolean flag for a changed quadrature
	'''

	#Add logic to add 1 to the dimension of an ADER case?	
	gorder = mesh.gorder
	shape = basis.__class__.__bases__[1].__name__

	# QuadOrder = 2*Order + 1
	if EqnSet is not None:
		QuadOrder = EqnSet.QuadOrder(order)
	else:
		QuadOrder = order
	if gorder > 1:
		dim = mesh.Dim
		QuadOrder += dim*(gorder-1)

	#is instance instead?
	if shape is 'QuadShape':
		QuadOrder += mesh.Dim
	QuadChanged = True

	if quadData is not None:
		if QuadOrder == quadData.order and shape == quadData.Shape:
			QuadChanged = False
	
	#Logic to subtract one if using ADER
	if EqnSet is not None:		
		if mesh.Dim == 1 and EqnSet.BasisADER is not 0:
			QuadOrder-=1

	return QuadOrder, QuadChanged


def get_gaussian_quadrature_face(mesh, IFace, basis, order, EqnSet=None, quadData=None):
	'''
	Method: get_gaussian_quadrature_face
	----------------------------------------
	Determines the quadrature order for the given face based on
	the basis functions, order, and equations.

	INPUTS:
		mesh: mesh object
		IFace: face object
		basis: polynomial basis function
		order: solution order 
		EqnSet: set of equations to be solved
		
	OUTPUTS:
		QuadOrder: quadrature order
		QuadChanged: boolean flag for a changed quadrature
	'''
	# assumes uniform QOrder and QBasis
	# QOrder = mesh.QOrder

	gorder = mesh.gorder
	shape = basis.__class__.__bases__[1].__name__
	faceshape = basis.faceshape.__class__.__name__
	# QuadOrder = 2*Order + 1
	if EqnSet is not None:
		QuadOrder = EqnSet.QuadOrder(order)
	else:
		QuadOrder = order
	if gorder > 1:
		dim = mesh.Dim - 1
		QuadOrder += dim*(gorder-1)

	# Shape = Basis.Basis2Shape[basis]
	# FShape = Basis.FaceShape[Shape]
	if shape is 'QuadShape':
		QuadOrder += basis.faceshape.dim

	QuadChanged = True
	if quadData is not None:
		if QuadOrder == quadData.order and faceshape == quadData.Shape:
			QuadChanged = False

	#Logic to subtract one if using ADER
	if EqnSet is not None:		
		if mesh.Dim == 1 and EqnSet.BasisADER is not 0:
			QuadOrder-=1

	return QuadOrder, QuadChanged


# def get_gaussian_quadrature_bface(mesh, BFace, basis, Order, EqnSet=None, quadData=None):
# 	# assumes uniform QOrder and QBasis
# 	QOrder = mesh.QOrder
# 	# QuadOrder = 2*Order + 1
# 	if EqnSet is not None:
# 		QuadOrder = EqnSet.QuadOrder(Order)
# 	else:
# 		QuadOrder = Order
# 	if QOrder > 1:
# 		dim = mesh.Dim - 1
# 		QuadOrder += dim*(QOrder-1)

# 	Shape = Basis.Basis2Shape[basis]
# 	FShape = Basis.FaceShape[Shape]
# 	if Shape is ShapeType.Quadrilateral:
# 		QuadOrder += Basis.Shape2Dim[FShape]

# 	QuadChanged = True
# 	if quadData is not None:
# 		if QuadOrder == quadData.Order and FShape == quadData.Shape:
# 			QuadChanged = False

# 	return QuadOrder, QuadChanged


class QuadData(object):
	'''
	Class: QuadData
	--------------------------------------------------------------------------
	This is a class defined to define the quadrature data for a given entity 
	(i.e. element, iface, or bface)
	'''
	def __init__(self,mesh,basis,entity,order):
		'''
		Method: __init__
		--------------------------------------------------------------------------
		This method initializes the quadrature data for a given entity. It uses the 
		mesh and basis to determine the shape of the entity as well as its dimension.
		It also uses the Order of the method to look up the following.

		ATTRIBUTES:
			quad_pts: Locations of points in reference space.
			quad_wts: Weight of the points in reference space.
			Shape: shape of the basis function
		'''
		dim = Mesh.get_entity_dim(mesh, entity)
		self.order = order
		
		self.qdim = mesh.Dim
		self.nvec = None

		# shape = Basis.Basis2Shape[basis]
		shape = basis.__class__.__bases__[1].__name__
		faceshape = basis.faceshape.__class__.__name__

		if entity == EntityType.Element:
			self.Shape = shape
		else:
			self.Shape = faceshape

		if self.Shape == 'PointShape':
			self.quad_pts = np.zeros([1,1])
			self.quad_wts = np.ones([1,1])
		elif self.Shape == 'SegShape':
			self.quad_pts, self.quad_wts = QuadratureRulesSeg.get_quadrature_points_weights(order, 0)
			# self.quad_pts = QuadLinePoints[order]
			# self.quad_wts = QuadLineWeights[order]
		elif self.Shape == 'QuadShape':
			self.quad_pts, self.quad_wts = QuadratureRulesQuad.get_quadrature_points_weights(order, 0)
			# self.quad_pts = QuadQuadrilateralPoints[order]
			# self.quad_wts = QuadQuadrilateralWeights[order]
		elif self.Shape == 'TriShape':
			self.quad_pts, self.quad_wts = QuadratureRulesTri.get_quadrature_points_weights(order, 0)
			# self.quad_pts = QuadTrianglePoints[order]
			# self.quad_wts = QuadTriangleWeights[order]
		else:
			raise NotImplementedError

class QuadDataADER(QuadData):
	pass
	# '''
	# Class: QuadData
	# --------------------------------------------------------------------------
	# This is a class defined to define the quadrature data for a given entity in ADER-DG
	# (i.e. element, iface, or bface)
	# '''
	# def __init__(self,mesh,basis,entity,order):
	# 	'''
	# 	Method: __init__
	# 	--------------------------------------------------------------------------
	# 	This method initializes the quadrature data for a given entity for the ADER-DG method. 
	# 	It uses the mesh and basis to determine the shape of the entity as well as its dimension.
	# 	It also uses the Order of the method to look up the following.

	# 	ATTRIBUTES:
	# 		quad_pts: Locations of points in reference space.
	# 		quad_wts: Weight of the points in reference space.
	# 		Shape: shape of the basis function
	# 	'''
	# 	#ADER is always one dimension greater than physcial space
	# 	dim = Mesh.get_entity_dim(mesh, entity) + 1
	# 	self.order = order
		
	# 	self.qdim = mesh.Dim + 1
	# 	self.nvec = None

	# 	# shape = Basis.Basis2Shape[basis]
	# 	shape = basis.__class__.__bases__[1].__name__
	# 	faceshape = basis.faceshape.__class__.__name__

	# 	if entity == EntityType.Element:
	# 		self.Shape = shape
	# 	else:
	# 		self.Shape = faceshape

	# 	if self.Shape == 'PointShape':
	# 		self.quad_pts = np.zeros([1,1])
	# 		self.quad_wts = np.ones([1,1])
	# 	elif self.Shape == 'SegShape':
	# 		self.quad_pts, self.quad_wts = QuadratureRulesSeg.get_quadrature_points_weights(order)
	# 		# self.quad_pts = QuadLinePoints[order]
	# 		# self.quad_wts = QuadLineWeights[order]
	# 	elif self.Shape == 'QuadShape':
	# 		self.quad_pts, self.quad_wts = QuadratureRulesQuad.get_quadrature_points_weights(order)
	# 		# self.quad_pts = QuadQuadrilateralPoints[order]
	# 		# self.quad_wts = QuadQuadrilateralWeights[order]
	# 	elif self.Shape == 'TriShape':
	# 		self.quad_pts, self.quad_wts = QuadratureRulesTri.get_quadrature_points_weights(order)
	# 		# self.quad_pts = QuadTrianglePoints[order]
	# 		# self.quad_wts = QuadTriangleWeights[order]
	# 	else:
	# 		raise NotImplementedError