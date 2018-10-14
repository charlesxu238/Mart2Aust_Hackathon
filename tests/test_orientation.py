import pytest
import numpy as np

from texpy.quaternion.orientation import Orientation
from texpy.quaternion.symmetry import *


@pytest.fixture
def vector(request):
    return Vector3d(request.param)

@pytest.fixture
def orientation(request):
    return Orientation(request.param)


@pytest.mark.parametrize('orientation, symmetry, expected', [
    ([(1, 0, 0, 0)], C1, [(1, 0, 0, 0)]),
    ([(1, 0, 0, 0)], C4, [(1, 0, 0, 0)]),
    ([(1, 0, 0, 0)], D3, [(1, 0, 0, 0)]),
    ([(1, 0, 0, 0)], T, [(1, 0, 0, 0)]),
    ([(1, 0, 0, 0)], O, [(1, 0, 0, 0)]),

    # 7pi/12 -C2-> # 7pi/12
    ([(0.6088, 0, 0, 0.7934)], C2, [(-0.7934, 0, 0, 0.6088)]),
    # 7pi/12 -C3-> # 7pi/12
    ([(0.6088, 0, 0, 0.7934)], C3, [(-0.9914, 0, 0, 0.1305)]),
    # 7pi/12 -C4-> # pi/12
    ([(0.6088, 0, 0, 0.7934)], C4, [(-0.9914, 0, 0, -0.1305)]),
    # 7pi/12 -O-> # pi/12
    ([(0.6088, 0, 0, 0.7934)], O, [(-0.9914, 0, 0, -0.1305)]),

], indirect=['orientation'])
def test_set_symmetry(orientation, symmetry, expected):
    o = orientation.set_symmetry(symmetry)
    assert np.allclose(o.data, expected, atol=1e-3)


@pytest.mark.parametrize('symmetry, vector', [
    (C1, (1, 2, 3)),
    (C2, (1, -1, 3)),
    (C3, (1, 1, 1)),
    (O, (0, 1, 0))
], indirect=['vector'])
def test_orientation_persistence(symmetry, vector):
    v = symmetry.outer(vector).flatten()
    o = Orientation.random()
    oc = o.set_symmetry(symmetry)
    v1 = o * v
    v1 = Vector3d(v1.data.round(4))
    v2 = oc * v
    v2 = Vector3d(v2.data.round(4))
    assert v1._tuples == v2._tuples