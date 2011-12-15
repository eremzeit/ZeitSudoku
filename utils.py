import pdb
import copy

def MultiDimList(sizes, func=lambda: None,_i=0):
    if _i < len(sizes) - 1:
        item = MultiDimList(sizes, func, _i+1)
    else:
        item = func()
    return [ copy.deepcopy(item) for x in xrange(sizes[_i]) ]

class SudokuChange:
    def __init__(self, coord, val, _hash=None):
        self.coord = coord
        self.hash = _hash #a hash of the board BEFORE the change

    @staticmethod
    def RemoveAlreadyKnown(board, changes):
        toRemove = []
        for change in changes:
            if isinstance(change, SudokuValueChange):
                #print change
                #pdb.set_trace()
                if board.GetVal(change.coord):
                    assert board.GetVal(change.coord) == change.value
                    toRemove.append(change)
            elif isinstance(change, SudokuElimChange):
                elims = set(board.GetElim(change.coord))
                alreadyElimed = set([1,2,3,4,5,6,7,8,9]) - elims
                change.valsToElim = list(set(change.valsToElim) - alreadyElimed)
                
                if len(change.valsToElim) == 0:
                    toRemove.append(change)
        for c in toRemove:
            if c in changes:
                changes.remove(c)
        return changes

class SudokuValueChange(SudokuChange):
    def __init__(self, coord, value, strat, board, _hash=None):
        self.coord = coord
        self.value = value
        self.hash = _hash #a hash of the board BEFORE the change
        self.strat = strat
        self.board = board
        self._validate()

    def __str__(self):
        return "<Set %s to %s, %s>" % (self.coord, self.value, self.strat.__name__)
    def __repr__(self):
        return self.__str__()

    def Apply (self, board):
        #if board.GetVal(self.coord):
        #    pdb.set_trace()
        board.SetVal(self.coord, self.value)
    
    def IsCoveredBy(self, change):
        if not isinstance(change, self.__class__): return False
        if self.coord == change.coord:
            if self.value != change.value: pdb.set_trace()
            return True
        return False

    def _validate(self):
        if not self.value in self.board.GetElim(self.coord):
            pdb.set_trace()
        newBoard = self.board.copy()
        self.Apply(newBoard)
        newBoard.Verify()

class SudokuElimChange(SudokuChange):
    def __init__(self, coord, valsToElim, strat, board, _hash=None):
        self.coord = coord
        self.valsToElim = valsToElim
        self.hash = _hash #a hash of the board BEFORE the change
        self.strat = strat
        self.board = board
        self._validate()

    def __str__(self):
        return "<Elim %s from %s, %s>" % (list(self.valsToElim), self.coord, self.strat.__name__)
    def __repr__(self):
        return self.__str__()
    
    def Apply (self, board):
        for val in self.valsToElim:
            board.Eliminate(self.coord, val)
    
    def IsCoveredBy(self, change):
        if not isinstance(change, self.__class__): return False
        if self.coord == change.coord and set(self.valsToElim) <= set(change.valsToElim):
            return True
        return False
    
    def _validate(self):
        val = self.board.GetVal(self.coord)
        if val and val in self.valsToElim:
            pdb.set_trace()
        res = set(self.board.GetElim(self.coord)) - set(self.valsToElim)
        if len(res) == 0:
            pdb.set_trace()
        newBoard = self.board.copy()
        self.Apply(newBoard)
        newBoard.Verify()

class SolvingRoundInfo:
    def __init__(self, roundNum, changes, stratOrdering, boardCopy):
        self.roundNum = roundNum
        self.changes = changes
        self.stratOrdering = stratOrdering
        self.boardCopy = boardCopy

        self._sortbyStrat()
        self._flatten()
    
    def _sortByStrat(self):
        self.changes.sort(key=lambda change: stratOrdering.index(change.strat)) 

    def _flatten(self):
        toRemove = []
        #if there exists a change by a simpler strategy that covers this change, remove this change
        for i in xrange(len(self.stratOrdering)):
            strat = self.stratOrdering[i]
            changes = filter(lambda c: c.strat == strat, self.changes)
            simplerChanges = filter(lambda c: c.strat in self.stratOrdering[0:i], self.changes)
            for change in changes:
                for simplerChange in simplerChanges:
                    if change.IsCoveredBy(simplerChange):
                        toRemove.append(change)
        for c in toRemove:
            self.changes.remove(c)

#The specified value must be in one of the positions listed
class ValueConstraint:
    def __init__(self, val, coords):
        self.val = val
        self.coords = set(coords)
    def __str__(self):
        return "<Value %s must be in %s" % (self.val, self.coords)

def ValsInSet(board, coordList):
    vals = []
    for coord in coordList:
        vals.append(board.GetVal(coord))
    return set(vals)

def GetVal(grid, coord):
    return grid[coord[0]][coord[1]]

def RowSudokuSet(row):
    l = [] 
    for col in xrange(0,9):
        l.append((row, col))
    return l

def ColSudokuSet(col):
    l = [] 
    for row in xrange(0,9):
        l.append((row, col))
    return l


quadCoordMap = []
def _makeQuadCoordMap():
    quadCoordMap = []
    for i in xrange(0,9):
        coords = []
        greaterRow = i / 3
        greaterCol = i % 3
        rowStart = greaterRow * 3
        colStart = greaterCol * 3
        for row in xrange(rowStart,rowStart + 3):
            for col in xrange(colStart, colStart + 3):
                coords.append((row,col))
        quadCoordMap.append(coords)
    return quadCoordMap
    #print quadCoordMap
    #print quadCoordMap[7][1]
    #pdb.set_trace()
quadCoordMap = _makeQuadCoordMap() 
assert quadCoordMap[7][1] == (6,4)

def QuadSudokuSetByQuad(quad):
    coords = quadCoordMap[quad]
    return coords
    #for coord in coords:
    #    yield coord

def QuadSudokuSetByCoord(coord):
    greaterRow = i / 3
    greaterCol = i % 3
    quad = greaterRow * 3 + greaterCol
    coords = quadCoordMap[quad]
    return coords

def GenerateValueConstraint(board, sudokuSet, val):
    posConstraints = []
    for pos in sudokuSet.coords:
        if val in board.elim[pos[0]][pos[1]]:
            posConstraints.append(pos)
    return ValueConstraint(val, posConstraints) 

def PrintStatus(board, coord):
    print board
    print 'Coord %s' % (str(coord))

    val = board.grid[coord[0]][coord[1]]
    elimList = board.elim[coord[0]][coord[1]]
    print 'val: %s\telim: %s\n\n' % (str(val), str(elimList))
    
class Condradiction(Exception):
    pass

#def IsContainedInAndOnlyIn(targetPosList, sudokuSets):
#    targetSudokuSet = set(targetPosList)
#    isContainedIn = []
#    for sudokuSet in sudokuSets:
#        if targetSudokuSet.issubset(set(sudokuSet.coords)):
#            isContainedIn.append(sudokuSet)
#    if len(isContainedIn) == 1:
#        return isContainedIn[0]
#    return null

class CounterDict(dict):
    def Increment(self, item, amount=1):
        if item in self:
            self[item] += amount
        else:
            self[item] = amount

class Parser():
    @staticmethod
    def Parse9Lines(lines):
        grid = [] 
        count = 0
        for line in lines:
            def convert(p):
                p = p.strip()
                if p == '':
                    return None
                else:
                    return int(p)
            parts = map(lambda p: convert(p), line.split(','))
            assert len(parts) == 9
            board[count] = parts
            count += 1
            
            if count > 8:
                return grid 
