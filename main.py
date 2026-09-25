from grid_lib import in_bounds, closest, neighbors_in_bounds

def main():
    width = int(input("Ширина поля: "))
    height = int(input("Висота поля: "))
    x = int(input("Координата X: "))
    y = int(input("Координата Y: "))

    if in_bounds(x, y, width, height):
        print(f"\n({x}, {y}) — в межах поля.")
        
        true_neigbours = neighbors_in_bounds(x, y, width, height)
        print(f"Доступні сусіди: {true_neigbours}")
        
        points = [(0, 0), (width - 1, height - 1), (width // 2, height // 2)] #(width // 2, height // 2) визначає центр поля
        nearest = closest(points, x, y)
        print(f"Найближча з {points} — це {nearest}")
        
    else:
        print(f"\nПомилка: ({x}, {y}) поза межами.")

if __name__ == "__main__":
    main()