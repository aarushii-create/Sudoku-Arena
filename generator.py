import random
import copy
from sudoku_engine import SudokuEngine

class SudokuGenerator(SudokuEngine):
    def __init__(self):
        super().__init__()

    def fill_grid(self, board):
        find = self.find_empty(board)
        if not find:
            return True
        row, col = find

        numbers = list(range(1, 10))
        random.shuffle(numbers)

        for num in numbers:
            if self.is_valid(board, row, col, num):
                board[row][col] = num
                if self.fill_grid(board):
                    return True
                board[row][col] = 0
        return False

    def count_solutions(self, board, count=0):
        find = self.find_empty(board)
        if not find:
            return count + 1
        
        row, col = find
        for num in range(1, 10):
            if self.is_valid(board, row, col, num):
                board[row][col] = num
                count = self.count_solutions(board, count)
                board[row][col] = 0
                if count > 1:
                    break
        return count

    def generate_puzzle(self, difficulty_level=30):
        board = [[0 for _ in range(9)] for _ in range(9)]
        self.fill_grid(board)
        full_solution = copy.deepcopy(board)

        attempts = 5
        while attempts > 0:
            row = random.randint(0, 8)
            col = random.randint(0, 8)
            while board[row][col] == 0:
                row = random.randint(0, 8)
                col = random.randint(0, 8)

            backup = board[row][col]
            board[row][col] = 0

            board_copy = copy.deepcopy(board)
            if self.count_solutions(board_copy) != 1:
                board[row][col] = backup
                attempts -= 1
            
            clues_left = sum(row.count(x) for row in board for x in range(1, 10))
            if clues_left <= difficulty_level:
                break

        return board, full_solution

if __name__ == "__main__":
    gen = SudokuGenerator()
    puzzle, solution = gen.generate_puzzle(difficulty_level=25)
    print("Generated Puzzle (0 = empty):")
    gen.print_board(puzzle)