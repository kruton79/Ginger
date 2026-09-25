from grid_lib import in_bounds, manhattan, neighbors, closest,neighbors_in_bounds
assert in_bounds(0, 0, 5, 5) == True
assert in_bounds(5, 5, 5, 5) == False 
assert in_bounds(0, 0, 0, 0) == False
assert manhattan(0, 0, 4, 4) == 8
assert manhattan(1, 2, 3, 4) == 4
assert manhattan(0, 0, 0, 0) == 0
assert neighbors(0, 0) == [(0, -1), (1, 0), (0, 1), (-1, 0)]
assert neighbors(1, 5) == [(1, 4), (2, 5), (1, 6), (0, 5)]
assert closest([(0, 0), (1, 1), (2, 2)], 1, 1) == (1, 1)
assert closest([], 0, 0) == None
assert closest([(5, 6), (2, 2)], 3, 4) == (2, 2)
assert neighbors_in_bounds(2,2,5,5)==[(2,1),(3,2),(2,3),(1,2)]
assert neighbors_in_bounds(0,0,5,5)==[(1,0),(0,1)]
