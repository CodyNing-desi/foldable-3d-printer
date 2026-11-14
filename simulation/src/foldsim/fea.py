import numpy as np
from skfem import Basis, ElementHex1, ElementVector, FacetBasis, LinearForm, MeshHex, condense, solve
from skfem.models.elasticity import lame_parameters, linear_elasticity


def solve_cantilever_beam(
    length_mm, width_mm, height_mm, E_MPa, poisson, tip_load_N,
    elements_along=20, elements_width=3, elements_height=3,
):
    x = np.linspace(0.0, length_mm, elements_along + 1)
    y = np.linspace(-width_mm / 2, width_mm / 2, elements_width + 1)
    z = np.linspace(-height_mm / 2, height_mm / 2, elements_height + 1)
    mesh = MeshHex.init_tensor(x, y, z)
    element = ElementVector(ElementHex1())
    basis = Basis(mesh, element, intorder=2)
    K = linear_elasticity(*lame_parameters(E_MPa, poisson)).assemble(basis)

    fixed_facets = mesh.facets_satisfying(lambda points: np.isclose(points[0], 0.0))
    tip_facets = mesh.facets_satisfying(lambda points: np.isclose(points[0], length_mm))
    fixed = basis.get_dofs(facets=fixed_facets).all()

    @LinearForm
    def traction(v, w):
        return -(tip_load_N / (width_mm * height_mm)) * v[2]

    tip_basis = FacetBasis(mesh, element, facets=tip_facets)
    f = traction.assemble(tip_basis)
    u = solve(*condense(K, f, D=fixed))

    tip_nodes = mesh.nodes_satisfying(lambda points: np.isclose(points[0], length_mm))
    z_dofs = basis.nodal_dofs[2, tip_nodes]
    fea_deflection = float(-np.mean(u[z_dofs]))
    second_moment = width_mm * height_mm**3 / 12
    beam_deflection = tip_load_N * length_mm**3 / (3 * E_MPa * second_moment)
    return {
        "fea_tip_deflection_mm": fea_deflection,
        "euler_bernoulli_tip_deflection_mm": beam_deflection,
        "relative_error": (fea_deflection - beam_deflection) / beam_deflection,
        "second_moment_mm4": second_moment,
        "elements": elements_along * elements_width * elements_height,
        "dofs": len(u),
        "displacement_mm": u,
    }
