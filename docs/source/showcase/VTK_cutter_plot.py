import k3d
import vtk
from vtk.util import numpy_support
import numpy as np
import pathlib

path = pathlib.Path(__file__).parent.resolve()

def generate():
    plot = k3d.plot(screenshot_scale=1.0)

    filename = str(path) + '/assets/output_fem.vtu'
    reader = vtk.vtkXMLUnstructuredGridReader()
    reader.SetFileName(filename)
    reader.Update()
    grid = reader.GetOutput()
    bbox = np.array(grid.GetBounds()).reshape(3, 2)
    center = np.mean(bbox, axis=1)

    plane = vtk.vtkPlane()
    plane.SetOrigin(*center)
    plane.SetNormal(1, 0.3, 0)

    def vtk_ExtractSurface(vtk_outputport, vtk_o, vtk_n):
        plane.SetOrigin(*vtk_o)
        plane.SetNormal(*vtk_n)

        myExtractGeometry = vtk.vtkExtractGeometry()
        myExtractGeometry.SetInputConnection(vtk_outputport)
        myExtractGeometry.SetImplicitFunction(plane)
        myExtractGeometry.ExtractInsideOn()
        myExtractGeometry.SetExtractBoundaryCells(0)
        myExtractGeometry.Update()

        myExtractSurface = vtk.vtkDataSetSurfaceFilter()
        myExtractSurface.SetInputConnection(myExtractGeometry.GetOutputPort())
        myExtractSurface.Update()

        return myExtractSurface.GetOutput()

    def update_from_cut(reader, vtk_o, vtk_n, plt_vtk):
        poly_data = vtk_ExtractSurface(reader.GetOutputPort(), vtk_o, vtk_n)
        if poly_data.GetNumberOfCells() > 0:
            vertices, indices, attribute = get_mesh_data(poly_data)
            with plt_vtk.hold_sync():
                plt_vtk.vertices = vertices
                plt_vtk.indices = indices
                plt_vtk.attribute = attribute

    def get_mesh_data(poly_data, color_attribute=('Umag', 0.0, 0.1)):

        if poly_data.GetPolys().GetMaxCellSize() > 3:
            cut_triangles = vtk.vtkTriangleFilter()
            cut_triangles.SetInputData(poly_data)
            cut_triangles.Update()
            poly_data = cut_triangles.GetOutput()

        if color_attribute is not None:
            attribute = numpy_support.vtk_to_numpy(
                poly_data.GetPointData().GetArray(color_attribute[0]))
            color_range = color_attribute[1:3]
        else:
            attribute = []
            color_range = []

        vertices = numpy_support.vtk_to_numpy(poly_data.GetPoints().GetData())
        indices = numpy_support.vtk_to_numpy(poly_data.GetPolys().GetData()).reshape(-1, 4)[:, 1:4]

        return (np.array(vertices, np.float32), np.array(indices, np.uint32),
                np.array(attribute, np.float32))

    vtk_n = np.array([0., .3, 0.])
    vtk_o = np.array([0.04984861, 20.03934663, 0.04888905])


    plt_vtk = k3d.vtk_poly_data(
        vtk_ExtractSurface(
            reader.GetOutputPort(),
            vtk_o, vtk_n
        ),
        color_attribute=('Umag', 0.0, 0.32),
        color_map=k3d.colormaps.paraview_color_maps.Cool_to_Warm,
        side='double')

    plt_vtk.flat_shading = True
    plot += plt_vtk

    plt_mesh = k3d.vtk_poly_data(vtk_ExtractSurface(reader.GetOutputPort(), vtk_o, vtk_n))

    plt_mesh.wireframe = True
    plt_mesh.color = 0xaaaaaa
    plt_mesh.opacity = 0.2

    plot += plt_mesh
    plot.camera = [0.064, 0.043, 0.043, 0.051, 0.041, 0.049, -0.059, 0.993, 0.087]

    update_from_cut(reader, center + 0.0, [1, 0, 0], plt_vtk)

    plot.snapshot_type = 'inline'

    return plot.get_snapshot()
