#! /usr/bin/env python3

import curses, sys

'''
    DiffWindow - a Python curses script to compare 2 text files
    Copyright (C) 2022  Chase Phelps

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''

'''
  DiffWindow
  ___________
  A class to be used in the manner "with DiffWindow() as win:"
    this usage keeps curses from messing up the terminal on ctrl-c/etc.
  An implementation of curses for side-by-side file comparison
  Takes 2 lists of strings.
    so, lhs = [line.strip() for line in lhsfile.readlines()]
        rhs = [line.strip() for line in rhsfile.readlines()]
  ___________
  Normal navigation keys allow scrolling:
    up, down, left, right, pgup, pgdown, home, end
  ___________
  Normal exit is by one of: escape, q, or Q
  ___________
  Default mode: both sides scroll together and matches highlighted
  ___________
  The 'space' key toggles independent/locked scrolling
  The 'tab' key switches between lhs/rhs for independent scrolling
  The keys d, D, h, or H toggle match highlighting
    (d for diff, h for highlight)
  When highlighting is enabled lhs/rhs lines that are the same
    **and are on the same level of the screen**
    will be highlighted
  ___________
  Example Usage:
    from diffwin import diffWindow
    def split_display(lhs = [''], rhs = ['']):
      with SplitWindow() as win:
        with open('curse.py','r') as infile:
          lhs = [line.strip() for line in infile.readlines()]
        with open('curse2.py','r') as infile:
          rhs = [line.strip() for line in infile.readlines()]
        win.listdiff(lhs,rhs)
'''
class DiffWindow:
  def __init__(self): pass
  '''
  __enter__

    We init curses, get a screen, and set options
    Returns self for use with the listdiff() function
  '''
  def __enter__(self):
    return self.initscr()

  '''
  __exit__

    We teardown curses and return the terminal to normal operation
  '''
  def __exit__(self, type, value, traceback):
    self.stopscr()

  '''
  __del__

    Delete for an improper usage
  '''
  def __del__(self):
    self.stopscr()

  '''
  initscr

    The actual init function to init curses and set vars
  '''
  def initscr(self):
    # flag init
    self.isinit = None
    # get the std screen
    self.stdscr = curses.initscr()
    # enable color output
    curses.start_color()
    # we can use pair numbers from 1 ... (0 is standard)
    # COLOR_ BLACK, BLUE, CYAN, GREEN, MAGENTA, RED, WHITE, YELLOW
    # This will be for green text on black
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    # suppress echo of keypresses
    curses.noecho()
    # immediately respond to keypresses
    curses.cbreak()
    # hide the cursor
    curses.curs_set(0)
    # enable to cursor to go out of bounds
    self.stdscr.scrollok(True)
    # enable use of curses info for curses.KEY_LEFT, etc.
    self.stdscr.keypad(True)
    return self

  '''
  stopscr

    The actual stop method to teardown the curses
  '''
  def stopscr(self):
    # reset modes back to normal
    curses.nocbreak()
    self.stdscr.keypad(False)
    curses.echo()
    curses.endwin()

  '''
  draw(lhs, lpos, rhs, rpos, dohighlight)

    This method repaints the screen
    lhs and rhs are lists of strings
    lpos and rpos determines which row/col is the top left
    the screen is divided vertically into 2 segments
    there is a small gap between lhs / rhs for readability
    the screen is cleared, strings added to screen, then refreshed
  '''
  def draw(self, lhs, lpos, rhs, rpos, dohighlight):
    height, width = self.stdscr.getmaxyx()
    # starting column for lhs -vs- rhs
    rstart = width//2 + 2
    # don't separate them by too much if we have extra space
    if rstart > self.lwidth + 6:
      rstart = self.lwidth + 6
    # lhs would stop 4 chars before rstart
    lstop = rstart - 4
    # rhs can use chars from rstart to width
    rstop = width-rstart
    # if the starting column is > 0 then we also shift the stop
    lstop += lpos[1]
    rstop += rpos[1]
    # the default color is standard color
    color = curses.color_pair(0)
    # clear the screen and add lines
    self.stdscr.erase()
    for i in range(height):
      if dohighlight:
        # if the strings match (without leading/trailing space)
        if i+lpos[0] < len(lhs) and i+rpos[0] < len(rhs) and \
              lhs[lpos[0]+i].strip() == rhs[rpos[0]+i].strip():
          # make bold green
          color = curses.color_pair(1) | curses.A_BOLD
        # otherwise standard color
        else: color = curses.color_pair(0)
      # draw lhs if we have a row here
      if i+lpos[0] < len(lhs):
        self.stdscr.addstr(i, 0, lhs[lpos[0]+i][lpos[1]:lstop], color)
      # draw rhs if we have a row here
      if i+rpos[0] < len(rhs):
        self.stdscr.addstr(i, rstart, rhs[rpos[0]+i][rpos[1]:rstop], color)
    self.stdscr.refresh()
    return height, width

  '''
  showdiff(lhs, rhs)

    This is the main driver function for this class
    Takes 2 lists of strings, lhs and rhs

    Returns when the escape, q, or Q key has been pressed
  '''
  def showdiff(self, lhs=[], rhs=[]):
    # handle if class is used improperly
    try:
      if not self.isinit: pass
    except AttributeError: self.initscr()
    # remove empty lines from lhs / rhs
    lhs = [line.rstrip() for line in lhs if line.strip() != '']
    rhs = [line.rstrip() for line in rhs if line.strip() != '']
    # get max columns to prevent scrolling too far right
    self.lwidth = 0
    for row in lhs:
      if len(row) > self.lwidth: self.lwidth = len(row)
    self.rwidth = 0
    for row in rhs:
      if len(row) > self.rwidth: self.rwidth = len(row)
    # track top left 'coordinate' of the text in the lists
    # the l/rpos is the startomg row + col to display
    lpos = [0,0] # lpos[0] is starting row
    rpos = [0,0] # rpos[1] is starting col
    # track the last known height/width as the window could be resized
    lastheight, lastwidth = self.stdscr.getmaxyx()
    # allow independent scrolling
    singlescroll = False
    # side toggle for independent scrolling
    leftscroll = True
    # toggle for whether to highlight matching lines
    dohighlight = True
    # these chars will quit: escape = 27, 'Q'=81, 'q'=113
    # we'll start at home
    ch = curses.KEY_HOME
    while ch not in [27, 81, 113]:
      # repaint the screen if we do one of these conditions
      repaint = True
      '''
        Commands
      '''
      # the space key to toggle independent scrolling
      if ch == 32: singlescroll = not singlescroll
      # the tab key to toggle whether lhs is active (otherwise rhs)
      elif ch == 9: leftscroll = not leftscroll
      # toggle line match highlight with d, D, h, or H (for diff/highlight)
      elif ch in [68, 72, 100, 104]: dohighlight = not dohighlight
      # reset positions
      elif ch == curses.KEY_HOME:
        if not singlescroll: lpos, rpos = [0,0], [0,0]
        elif leftscroll: lpos = [0,0]
        else: rpos = [0,0]
      # go to the bottom
      elif ch == curses.KEY_END:
        if not singlescroll or leftscroll:
          # fit our maxheight in the last known height
          if lastheight < len(lhs):
            lpos[0] = len(lhs) - lastheight
        if not singlescroll or not leftscroll:
          if lastheight < len(rhs):
            rpos[0] = len(rhs) - lastheight
      # page up
      elif ch == curses.KEY_PPAGE:
        if not singlescroll or leftscroll:
          lpos[0] -= lastheight - 4
          if lpos[0] < 0: lpos[0] = 0
        if not singlescroll or not leftscroll:
          rpos[0] -= lastheight - 4
          if rpos[0] < 0: rpos[0] = 0
      # page down
      elif ch == curses.KEY_NPAGE:
        if not singlescroll or leftscroll:
          if lastheight < len(lhs):
            lpos[0] += lastheight - 4
            if lpos[0] > len(lhs) - lastheight:
              lpos[0] = len(lhs) - lastheight
        if not singlescroll or not leftscroll:
          if lastheight < len(rhs):
            rpos[0] += lastheight - 4
            if rpos[0] > len(rhs) - lastheight:
              rpos[0] = len(rhs) - lastheight
      # scroll up
      elif ch == curses.KEY_UP:
        if not singlescroll or leftscroll:
          if lpos[0] > 0: lpos[0] -= 1
        if not singlescroll or not leftscroll:
          if rpos[0] > 0: rpos[0] -= 1
      # scroll down
      elif ch == curses.KEY_DOWN:
        if not singlescroll or leftscroll:
          if lastheight < len(lhs):
            if lpos[0] < len(lhs) - lastheight: lpos[0] += 1
        if not singlescroll or not leftscroll:
          if lastheight < len(rhs):
            if rpos[0] < len(rhs) - lastheight: rpos[0] += 1
      # scroll left
      elif ch == curses.KEY_LEFT:
        if not singlescroll or leftscroll:
          if lpos[1] > 0: lpos[1] -= 1
        if not singlescroll or not leftscroll:
          if rpos[1] > 0: rpos[1] -= 1
      # scroll right
      elif ch == curses.KEY_RIGHT:
        if not singlescroll or leftscroll:
          if lastwidth//2 - 2 < self.lwidth:
            if lpos[1] < self.lwidth - lastwidth//2 + 2: lpos[1] += 1
        if not singlescroll or not leftscroll:
          if lastwidth//2 - 2 < self.rwidth:
            if rpos[1] < self.rwidth - lastwidth//2 + 2: rpos[1] += 1
      else:
        # If we didn't change the pos then don't repaint
        repaint = False
      if repaint: lastheight, lastwidth = self.draw(lhs, lpos,
                                                    rhs, rpos,
                                                    dohighlight)
      ch = self.stdscr.getch()

'''
When ran as a script will diff 2 files
'''
if __name__ == '__main__':
  if len(sys.argv) != 3:
    print('DiffWindow - a Python curses script to compare 2 text files\n')
    print('Usage:')
    print('python3',sys.argv[0],'file1 file2\n')
    print('Controls:')
    print('Quit:                              escape, q, Q')
    print('Toggle match highlighting:         d, D, h, H')
    print('Toggle left/right pane lock:       space')
    print('Toggle left/right pane scrolling:  tab')
    sys.exit(0)
  lhs, rhs = [], []
  with open(sys.argv[1]) as infile:
    lhs = infile.readlines()
  with open(sys.argv[2]) as infile:
    rhs = infile.readlines()
  # proper usage
  with DiffWindow() as win:
    win.showdiff(lhs, rhs)
  # improper usage
  #win = DiffWindow()
  #win.showdiff(lhs, rhs)
