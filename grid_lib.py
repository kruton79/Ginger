def in_bounds(x, y, width, height):
    '''перевіряє, чи знаходяться координати (x, y) в межах заданої ширини та висоти''' 
    return (0 <= x < width) and (0 <= y < height)
def manhattan(x1, y1, x2, y2):
    """манхеттенська відстань між двома точками (x1, y1) та (x2, y2)"""
    return abs(x1 - x2) + abs(y1 - y2)
def neighbors(x, y):
    """видає список сусідніх пар координат (x, y) на сітці"""
    return [(x, y - 1), (x + 1, y), (x, y + 1), (x - 1, y)]
def closest(points, x, y):
    """знаходить точку з списку points, яка є найближчою до координат (x, y) за манхеттенською відстанню"""
    if len(points) == 0:
        return None
    best_point = points[0]  #Беру першу точку як початкову найкращу
    best_dist = manhattan(best_point[0], best_point[1], x, y)
   
    for i in points: # Перебираю всі точки в списку points
        dist = manhattan(i[0], i[1], x, y)
        if dist < best_dist:
            best_dist = dist
            best_point = i
            
    return best_point
def neighbors_in_bounds(x, y, width, height):
    '''список сусідів,що знаходяться в межах сітки'''
    true_neigbours= []
    for ix, iy in neighbors(x,y):
        if in_bounds(ix, iy, width, height):
            true_neigbours.append((ix,iy))
    return true_neigbours       
