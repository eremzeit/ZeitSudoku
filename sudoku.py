import copy
from strats import *
from utils import *
import cProfile
import pstats
import pdb

class SudokuSet:
    def __init__(self, coords, typeStr=None):
        self.coords = set(coords)
        self.neighborOverlap = {}
        self.neighbors = set([])
        self.typeStr = typeStr

    def AddNeighbor(self, neighbor):
        self.neighbors.add(neighbor)
        self.neighborOverlap[neighbor] = set(filter(lambda coord: coord in self.coords, neighbor.coords))
        if set(neighbor.coords) <= self.coords: #neighbor should not be a subset
            print self.coords 
            print neighbor.coords
            pdb.set_trace()

class Board:
    def __str__(self):
        res = '' 
        for row in xrange(len(self.grid)):
            s = ''
            for col in xrange(len(self.grid[row])):
                val = self.grid[row][col]
                val = str(val) if val else ' '
                if col % 3 == 0:
                    s = s + ' . %s' % val
                else:
                    s = s + '  %s' % val
            if row == 0:
                res = s
            elif row % 3 == 0 and row > 0:
                res += '\n' + '. ' * (len(s) / 2) +  '\n' + s
            else:
                res += '\n\n' + s
        res += '\n\n'
        return res

    @property
    def hash(self):
        p = 0
        for row in xrange(len(self.grid)):
            for col in xrange(len(self.grid[row])):
                _t = ((row * 8) +  col) << 4 + self.grid[row][col]
                p ^= _t

    def IsSame(self, b2):
        for row in xrange(len(self.grid)):
            for col in xrange(len(self.grid[row])):
                if self.grid[row][col] != b2.grid[row][col]: return False
                if set(self.elim[row][col]) != set(b2.elim[row][col]): return False
        return True
        #if self.grid != b2.grid: return False
        #if self.elim != b2.elim: return False
        #return True
    def copy (self):
        b = self.__class__(self.grid)
        b.orig = copy.deepcopy(self.orig)
        b.elim = copy.deepcopy(self.elim)
        assert self.IsSame(b)
        return b
    def IsSolved(self):
        for row in xrange(len(self.grid)):
            for col in xrange(len(self.grid[row])):
                if not self.GetVal((row,col)): return False
        return True

    def GetVal(self, coord):
        return self.grid[coord[0]][coord[1]]
    def GetElim(self, coord):
        return self.elim[coord[0]][coord[1]]

    def SetVal(self, coord, val):
        assert val in self.elim[coord[0]][coord[1]]
        self.elim[coord[0]][coord[1]] = [val]
        if self.grid[coord[0]][coord[1]]:
            return
        self.grid[coord[0]][coord[1]] = val
        self.Verify()
        #for sudokuSet in self.mapCoordToSets[coord[0]][coord[1]]:
        #    self.UpdateElimBySet(sudokuSet)
    
    def Eliminate(self, coord, val):
        valAtCoord = self.GetVal(coord)
        if valAtCoord and valAtCoord == val:
            raise Condradiction()
        
        elif valAtCoord:
            self.elim[coord[0]][coord[1]] = [valAtCoord]
            return
        
        elimList = self.elim[coord[0]][coord[1]]
        assert len(elimList) == len(set(elimList))
        if val in elimList:
            elimList.remove(val)
        if not elimList: 
            pdb.set_trace() 
            raise Condradiction("Tried to remove %s but can't have an empty elim list at %s" % (coord, val))
        self.elim[coord[0]][coord[1]] = elimList 
    
    def Verify(self):
        #don't have duplicates
        for sudokuSet in self.sudokuSets:
            vals = set([])
            for coord in sudokuSet.coords:
                val = self.GetVal(coord)
                if val in vals:
                    if not self.isFake: pdb.set_trace()
                    raise Condradiction("Duplicate values detected: %s at %s" % (str(vals), str(coord)))
                if val: 
                    vals.add(val)
        #sync between grid and elim
        for row in xrange(len(self.grid)):
            for col in xrange(len(self.grid[row])):
                val = self.grid[row][col]
                if val:
                    if not val in self.elim[row][col] or len(self.elim[row][col]) == 0:
                        print '---\n'*3 + '! Board and elim not synced'
                        PrintStatus(self, (row,col))
                        pdb.set_trace()

    #def initElim(self):
    #    for row in xrange(len(self.grid)):
    #        for col in xrange(len(self.grid[row])):
    #            if self.GetVal((row,col)):
    #                self.Eliminate((row, col), val
    #    

class Board8x8(Board):
    def __init__(self, origBoard, isFake=False):
        self.orig = origBoard
        self.grid = copy.deepcopy(origBoard)
        self.elim = MultiDimList([9,9], lambda: range(1,10))
        self.isFake = isFake
        self.initSudokuSetList()
        self.initMapCoordToSets()
    
    
    def initSudokuSetList(self):
        rowSets = []
        colSets = []
        quadSets = []
        for i in xrange(0,9):
            rowSets.append(SudokuSet(RowSudokuSet(i), 'row:%s' % i))
            colSets.append(SudokuSet(ColSudokuSet(i), 'col:%s' % i))
            quadSets.append(SudokuSet(QuadSudokuSetByQuad(i), 'quad:%s' % i))
            
        for rowSet in rowSets:
            for colSet in colSets:
                rowSet.AddNeighbor(colSet)
                colSet.AddNeighbor(rowSet)
                
        for rowSet in rowSets:
            for quadSet in colSets:
                rowSet.AddNeighbor(quadSet)
                quadSet.AddNeighbor(rowSet)

        for colSet in colSets:
            for quadSet in quadSets:
                colSet.AddNeighbor(quadSet)
                quadSet.AddNeighbor(colSet)
        self.sudokuSetsRows = rowSets
        self.sudokuSetsCols = colSets
        self.sudokuSetsQuads = quadSets
        self.sudokuSets = rowSets + colSets + quadSets
    def initMapCoordToSets(self):
        self.mapCoordToSets = MultiDimList([9,9], lambda: [])
        for row in xrange(0,9):
            for col in xrange(0,9):
                self.mapCoordToSets[row][col] = filter(lambda posSet: (row, col) in posSet.coords, self.sudokuSets)
        assert len(self.mapCoordToSets[3][2]) == 3
        assert len(self.mapCoordToSets[8][8]) == 3
        assert len(self.mapCoordToSets[4][4]) == 3
    
    @staticmethod
    def FromFile8x8(filename):
        f = open('boards.txt', 'r')
        lines = f.read().split('\n')
        f.close()  
        boards = []
        solutions = []
        board = None
        count = 0
        
        lines = filter (lambda line: not (line.startswith('#') or line.strip() == ''), lines)

        #for line in lines:
        #    isSolution = False
        #    if line.strip().startswith('*'):
        #        isSolution = True
        #        line = line.strip()[1:]
        #     
        #    if count == 0:
        #        board = MultiDimList([9,9], lambda: None)
        #   
        #    if len(boards) == 1 an len(solutions) == 1:
        #        return boards
        return boards
    
    @property
    def Coords(self):
        for row in xrange(len(self.grid)):
            for col in xrange(len(self.grid[row])):
                yield (row, col)

def TestSolveAll():
    boards = Board8x8.FromFile8x8('boards.txt')
    for board in boards: 
        Solve(board).go()
        if not board.IsSolved():
            print board
            print "Couldn't be solved"

def ProfileTest():
    boards = Board8x8.FromFile8x8('boards.txt')
    b = boards[0]
    print b
    Solve(b, limit=10).go()
    print b

def Profile():
    cProfile.run('ProfileTest()', 'profileout')
    p = pstats.Stats('profileout') 
    p.sort_stats('cumulative').print_stats()

def Test():
    boards = Board8x8.FromFile8x8('boards.txt')
    b = boards[0]
    print b
    Solve(b).go()
    print b

if __name__ == "__main__":
    #Profile()
    Test()
