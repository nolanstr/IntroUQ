import jax.numpy as np
import os

import time
from scipy.stats import norm
from tqdm import tqdm
import pickle


from jax_fem.problem import Problem
from jax_fem.solver import solver
from jax_fem.utils import save_sol
from jax_fem.generate_mesh import box_mesh, get_meshio_cell_type, Mesh
from jax_fem import logger

import logging
logger.setLevel(logging.DEBUG)


class LinearElasticity(Problem):

    def material_parameters_init(self, E, nu):
        self.E = E
        self.nu = nu

    def get_tensor_map(self):

        def stress(u_grad):
            mu = self.E / (2. * (1. + self.nu))
            lmbda = self.E * self.nu / ((1 + self.nu) * (1 - 2 * self.nu))
            epsilon = 0.5 * (u_grad + u_grad.T)
            sigma = lmbda * np.trace(epsilon) * np.eye(
                self.dim) + 2 * mu * epsilon
            return sigma
        return stress

    def get_surface_maps(self):
        def surface_map(u, x):
            return np.array([0., 0., 100.])
        return [surface_map]

def run_model(E, nu, filename):
    ele_type = 'TET10'
    cell_type = get_meshio_cell_type(ele_type)
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    Lx, Ly, Lz = 10., 2., 2.
    Nx, Ny, Nz = 20, 2, 2
    meshio_mesh = box_mesh(Nx=Nx,
                           Ny=Ny,
                           Nz=Nz,
                           Lx=Lx,
                           Ly=Ly,
                           Lz=Lz,
                           data_dir=data_dir,
                           ele_type=ele_type)
    mesh = Mesh(meshio_mesh.points, meshio_mesh.cells_dict[cell_type])

    def left(point):
        return np.isclose(point[0], 0., atol=1e-5)

    def right(point):
        return np.isclose(point[0], Lx, atol=1e-5)

    def zero_dirichlet_val(point):
        return 0.

    dirichlet_bc_info = [[left] * 3, [0, 1, 2], [zero_dirichlet_val] * 3]

    location_fns = [right]
    problem = LinearElasticity(mesh,
                               vec=3,
                               dim=3,
                               ele_type=ele_type,
                               dirichlet_bc_info=dirichlet_bc_info,
                               location_fns=location_fns)
    problem.material_parameters_init(E, nu)

    sol_list = solver(problem, linear=True, use_petsc=True)
    displacements = sol_list[0]
    coords = problem.mesh[0].points
    data = {"coords":coords, 
            "displacements":displacements,
            "E":E,
            "nu":nu}
    FILE = open(f"model_outputs/{filename}.pkl", "wb")
    pickle.dump(data, FILE)
    FILE.close()
    #vtk_path = os.path.join(data_dir, 'vtk/u.vtu')
    #save_sol(problem.fes[0], sol_list[0], vtk_path)


if __name__ == "__main__":
    CV = 0.1
    E_mu = 70e3
    nu_mu = 0.3
    E_dist = norm(loc=E_mu, scale=CV * E_mu)
    nu_dist = norm(loc=nu_mu, scale=CV * nu_mu)

    N = 1000
    data = []
    for i in tqdm(range(N), total=N):
        E = E_dist.rvs()
        nu = nu_dist.rvs()
        tag = str(i+1).zfill(3)
        filename = f"output_{tag}"
        run_model(E, nu, filename)
