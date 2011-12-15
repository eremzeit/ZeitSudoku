from utils import *
import copy
import sys


class Strategy:
    def __init__(self, board):
        self.board = board
    
    @property
    def SudokuSets(self):
        return self.board.sudokuSets
    
    @property
    def MapCoordToSets(self):
        return self.board.mapCoordToSets

    #returns any changes to board that were found
    def Run(self):
        print 'Running %s' % self.__class__.__name__
        origBoard = self.board
        self.board = origBoard.copy()

        changes = self.go()

        Strategy.sort(changes)
        if len(changes) > 1000: 
            print self.__class__.__name__ ,len(changes)
            pdb.set_trace()
        changes = SudokuChange.RemoveAlreadyKnown(origBoard, changes)
        for change in changes:
            if isinstance(change, SudokuValueChange):
                print 'Changes made by %s' % (self.__class__.__name__)
            elif isinstance(change, SudokuElimChange):
                pass
        return changes
    
    @staticmethod
    def sort(changes):
        def compare(coord1, coord2):
            if coord1[0] < coord2[0]:
                return 1
            elif coord1[0] == coord2[0]:
                if coord1[1] < coord2[1]:
                    return 1
                elif coord1[1] == coord2[1]:
                    return 0 
                else:
                    return -1
            else:
                return -1
        changes.sort(cmp=compare, key=lambda change: change.coord) 

    #stub
    def go(self):
        pass

class FullSolver:
    def Solve(self, board):
        print board
        strats = [SimpleElimination, ValueConstrainedInSet, SetsOverlapStrategy, NakedSubsetStrategy, TrialAndError]
        
        
        roundInfos = []
        while True:
            changes = []
            for strat in strats:
                pdb.set_trace()
                _changes = strat(board).Run()
                changes += _changes
            if changes:
                roundInfos.append(SolvingRoundInfo(len(roundInfos), _changes, strats, board.Copy()))
                for change in changes:
                    print '.'
                    try:
                        change.Apply(board)
                    except Condradiction:
                        raise
                    except:
                        pdb.set_trace()
            else:
                break
        
        if board.IsSolved():
            s = 'solved!'
        else:
            s = 'stumped'
        print s + '\n' * 4
        print board

class Solve(Strategy):
    def __init__(self, board, limit=10000):
        self.board = board
        self.limit = limit

    def go(self):
        changes = []
        #strats = [SimpleElimination, ValueConstrainedInSet, SetsOverlapStrategy, TrialAndError, NakedSubsetStrategy]
        strats = [SimpleElimination, ValueConstrainedInSet, SetsOverlapStrategy,]
        stratIndex = 0
      
        __oldBoard = None
        count = 0
        while stratIndex < len(strats) and count < self.limit:
            count += 1
            strat = strats[stratIndex]

            __oldBoard = self.board.copy()
            try: 
                changes = strat(self.board).Run()
            except Condradiction:
                if self.board.isFake:
                    raise
                pdb.set_trace()
            
            for change in changes:
                if isinstance(change, SudokuElimChange):
                    val = self.board.GetVal(change.coord)
                    if val and val in change.valsToElim:
                        print change
                        pdb.set_trace()
                        pass
            if changes:
                for change in changes:
                    try:
                        change.Apply(self.board)
                    except Condradiction: 
                        raise
                    except Exception as e:
                        print e
                        pdb.set_trace()
                        pass
                stratIndex = 0
                
                if self.board.IsSame(__oldBoard):
                    print changes 
                    pdb.set_trace()
                    self.board.IsSame(__oldBoard)
            else:
                stratIndex += 1

def updateElimByCoord (board, tCoord, applyChanges=False):
    changes = []
    if board.GetVal(tCoord):
        return changes
    elims = board.GetElim(tCoord)
    sudokuSets = GetVal(board.mapCoordToSets, tCoord)
    
    valsToElim = set([])
    for sudokuSet in sudokuSets:
        for coord in sudokuSet.coords:
            if coord != tCoord:
                val = board.GetVal(coord)
                if not val: continue
                if val in elims:
                    valsToElim.add(val)
    changes.append(SudokuElimChange(tCoord, valsToElim, SimpleElimination, board))
    for val in valsToElim:
        if applyChanges:
            pdb.set_trace() 
            board.Eliminate(tCoord, val)
    return changes

def UpdateElim(board):
    changes = []
    for coord in board.Coords:
        changes = changes + updateElimByCoord(board, coord)
    return changes

#eliminates values for a coord if they exist in a Sudoku Set
class SimpleElimination(Strategy):
    def updateValsFromElim(self):
        changes = []
        for row, col in self.board.Coords:
            elimList = self.board.elim[row][col]
            if len(elimList) == 1:
                val = self.board.GetVal((row,col))
                
                if val and val != elimList[0] and not self.board.isFake:
                    pdb.set_trace()
                    pass
                changes.append( SudokuValueChange((row,col), elimList[0], self.__class__, self.board))
                self.board.SetVal((row,col), elimList[0])
        return changes
     
    def go(self):
        changes = UpdateElim(self.board)
        changes = changes + self.updateValsFromElim()
        return changes
                    
#if a value can't be anywhere else in the set besides one position, then we know it must be at that position
class ValueConstrainedInSet(Strategy):
    def processSet(self, sudokuSet):
        changes = []
        for val in xrange(1,10):
            presentVals = ValsInSet(self.board, sudokuSet.coords)
            #changes = changes + UpdateElim(self.board)
            constraint = GenerateValueConstraint(self.board, sudokuSet, val)
            if len(constraint.coords) == 1:
                coord = list(constraint.coords)[0]
                if not self.board.GetVal(coord):
                    changes.append(SudokuValueChange(coord, val, self.__class__, self.board))
                    self.board.SetVal(coord, val)
        return changes

    def go(self):
        changes = []
        for sudokuSet in self.SudokuSets:
            changes = changes + self.processSet(sudokuSet)
        return changes

class SetsOverlapStrategy(Strategy):
    def go(self):
        changes = []
        for sudokuSet in self.SudokuSets:
            for val in xrange(1,10):
                constraint = GenerateValueConstraint(self.board, sudokuSet, val)
                for neighbor in sudokuSet.neighbors:
                    if constraint.coords <= neighbor.coords:  #then all the other coords in this SudokuSet can be elim for that that value
                        coordsToEliminate = neighbor.coords - constraint.coords
                        for coordToElim in coordsToEliminate:
                            if val in self.board.GetElim(coordToElim):
                                changes.append(SudokuElimChange(coordToElim, [val], self.__class__, self.board))
                            #self.board.Eliminate(coordToElim, val)
        return changes

class NakedSubsetStrategy(Strategy):
    def go(self):
        changes = []
        for sudokuSet in self.SudokuSets:
            coords = list(sudokuSet.coords)
            size = len(sudokuSet.coords)
            
            elimSetCounts = {}
            i, j = 0,0
            for i in xrange(0,size):
                #for j in xrange(i+1,size):
                coord = coords[i]
                
                e = self.board.elim[coord[0]][coord[1]]
                e.sort()
                e = tuple(e)

                if not e in elimSetCounts: 
                    elimSetCounts[e] = 1
                else:
                    elimSetCounts[e] += 1

            nakedSubsets = []
            for elimSet in elimSetCounts.keys():
                if len(elimSet) == elimSetCounts[elimSet]:
                    nakedSubsets.append(set(elimSet))
            
            for i in xrange(0,size):
                coord = coords[i]
                e = set(self.board.elim[coord[0]][coord[1]])
                for nakedSubset in nakedSubsets:
                   if nakedSubset == e: continue
                   for val in nakedSubset:
                       changes.append(SudokuElimChange(coord, [val], self.__class__, self.board))
                       #self.board.Eliminate(coord, val)
        return changes


class ForcedChaining(Strategy):
   pass 

class XWing(Strategy):
   pass 


                    




class TrialAndError(Strategy):
    def go(self):
        changes = []
        b = self.board.copy()
        b.isFake = True
        for coord in b.Coords:
            val = b.GetVal(coord)
            elimList = b.GetElim(coord)
            if not val and len(elimList) == 2:
                testVal = elimList[0]
                b.SetVal(coord, testVal) 
                try: 
                    Solve(b).go()
                except Condradiction:
                    changes.append(SudokuElimChange(coord, [testVal], self.__class__, self.board))
                    #self.board.Eliminate(coord, testVal)
                if b.IsSolved():
                    changes.append(SudokuValueChange(coord, testVal, self.__class__, self.board))
                    #self.board.SetVal(coord, testVal)
        return changes
