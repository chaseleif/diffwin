#! /usr/bin/env python3

import curses, os, sys

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
  The '+' and '-' keys (plus/minus) will shift the pane separator left/right
  The '=' key will reset the pane shift
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
  '''
  __init__

    set unsafe flag which can allow usage without enter/exit
    The intended usage is as described above and in the name==__main__ usage
  '''
  def __init__(self, unsafe=False): self.unsafe = unsafe

  '''
  __enter__

    We init curses, get a screen, and set options
    Returns self for use with the listdiff() function
  '''
  def __enter__(self):
    self.unsafe = False
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
    try:
      if self.havescr: self.stopscr()
    except AttributeError: pass

  '''
  initscr

    The actual init function to init curses and set vars
  '''
  def initscr(self):
    # flag init
    self.havescr = True
    # get the std screen
    self.stdscr = curses.initscr()
    # enable color output
    curses.start_color()
    # we can use pair numbers from 1 ... (0 is standard)
    # COLOR_ BLACK, BLUE, CYAN, GREEN, MAGENTA, RED, WHITE, YELLOW
    # This will be for standard text
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    # This will be for title text
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
    # This will be error text
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
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
    self.havescr = False
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
  def draw(self, lhs, lpos, rhs, rpos, dohighlight, paneshmt):
    # clear the screen
    self.stdscr.erase()
    # the current height and width (will change if window is resized)
    height, width = self.stdscr.getmaxyx()
    # starting column for lhs -vs- rhs, lhs will always start at column 0
    rstart = width//2 + 2
    # don't separate them by too much if we have extra space
    if rstart > self.lwidth + 4:
      rstart = self.lwidth + 4
    # we use the l and rstop to determine ending index of printed string
    # lhs would stop 4 chars before rstart
    lstop = rstart - 4
    # rhs can use chars from rstart to width
    rstop = width-rstart
    # if the starting column is > 0 then we also shift the stop
    lstop += lpos[1]
    rstop += rpos[1]
    infocolor = curses.color_pair(2) | curses.A_BOLD
    # shift boundary left or right
    if paneshmt != 0:
      # paneshmt will be negative or positive
      lstop += paneshmt
      rstart += paneshmt
      # if the lstop or rstart have moved out of bounds to the left
      if lstop <= lpos[1] or rstart <= 4:
        # rhs uses the entire width
        lstop = lpos[1]
        rstart = 0
        rstop = width+rpos[1]
        self.stdscr.addstr(0, width-11, 'right file', infocolor)
      # if the rstart moved out of bounds to the right
      elif rstart >= width-4:
        rstart = 0
        rstop = rpos[1]
        lstop = width+lpos[1]
        self.stdscr.addstr(0, 1, 'left file', infocolor)
      # otherwise the boundary is still in the middle
      else:
        self.stdscr.addstr(0, 1, 'left file', infocolor)
        self.stdscr.addstr(0, width-11, 'right file', infocolor)
        rstop = width-rstart+rpos[1]
    else:
      self.stdscr.addstr(0, 1, 'left file', infocolor)
      self.stdscr.addstr(0, width-11, 'right file', infocolor)
    # the default color is standard color
    color = curses.color_pair(0)
    # add lines
    for i in range(1, height):
      if dohighlight:
        # if the strings match (without leading/trailing space)
        if i+lpos[0] < len(lhs) and i+rpos[0] < len(rhs) and \
              lhs[lpos[0]+i].strip() == rhs[rpos[0]+i].strip():
          # make bold green
          color = curses.color_pair(1) | curses.A_BOLD
        # otherwise standard color
        else: color = curses.color_pair(0)
      # draw lhs if we have a row here
      if lstop != lpos[1]:
        if i+lpos[0] < len(lhs):
          self.stdscr.addstr(i, 0, lhs[lpos[0]+i][lpos[1]:lstop], color)
        elif i+lpos[0] == len(lhs):
          self.stdscr.addstr(i, 1, '<End of file>', infocolor)
      # draw rhs if we have a row here
      if rstop != rpos[1]:
        if i+rpos[0] < len(rhs):
          self.stdscr.addstr(i, rstart, rhs[rpos[0]+i][rpos[1]:rstop], color)
        elif i+rpos[0] == len(rhs):
          self.stdscr.addstr(i, width-14, '<End of file>', infocolor)
    self.stdscr.refresh()
    return height, width

  '''
  showdiff(lhs, rhs)

    This is the main driver function for this class
    Takes 2 lists of strings, lhs and rhs

    Returns when the escape, q, or Q key has been pressed
  '''
  def showdiff(self, lhs=[], rhs=[]):
    # confirm class usage
    try:
      if not self.havescr: self.initscr()
    except AttributeError:
      if self.unsafe: self.initscr()
      else:
        raise AssertionError('unsafe is not true and curses not initialized')
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
    # shift amount for pane boundary, division between lhs/rhs views
    paneshmt = 0
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
      # plus key to shift pane separator right
      elif ch == 43:
        if lastwidth//2 - 10 + paneshmt < self.lwidth - lpos[1]: paneshmt += 1
      # minus key to shift pane separator left
      elif ch == 45:
        if lastwidth//2 + paneshmt < self.rwidth - lpos[1]: paneshmt -= 1
      # equal key to reset pane shift
      elif ch == 61: paneshmt = 0
      # reset positions
      elif ch == curses.KEY_HOME:
        if not singlescroll: lpos, rpos = [-1,0], [-1,0]
        elif leftscroll: lpos = [-1,0]
        else: rpos = [-1,0]
      # go to the bottom
      elif ch == curses.KEY_END:
        if not singlescroll or leftscroll:
          # fit our maxheight in the last known height
          if lastheight < len(lhs):
            lpos[0] = len(lhs) - lastheight + 1
        if not singlescroll or not leftscroll:
          if lastheight < len(rhs):
            rpos[0] = len(rhs) - lastheight + 1
      # page up
      elif ch == curses.KEY_PPAGE:
        if not singlescroll or leftscroll:
          lpos[0] -= lastheight - 4
          if lpos[0] < 0: lpos[0] = -1
        if not singlescroll or not leftscroll:
          rpos[0] -= lastheight - 4
          if rpos[0] < 0: rpos[0] = -1
      # page down
      elif ch == curses.KEY_NPAGE:
        if not singlescroll or leftscroll:
          if lastheight < len(lhs):
            lpos[0] += lastheight - 4
            if lpos[0] > len(lhs) - lastheight:
              lpos[0] = len(lhs) - lastheight + 1
        if not singlescroll or not leftscroll:
          if lastheight < len(rhs):
            rpos[0] += lastheight - 4
            if rpos[0] > len(rhs) - lastheight:
              rpos[0] = len(rhs) - lastheight + 1
      # scroll up
      elif ch == curses.KEY_UP:
        if not singlescroll or leftscroll:
          if lpos[0] >= 0: lpos[0] -= 1
        if not singlescroll or not leftscroll:
          if rpos[0] >= 0: rpos[0] -= 1
      # scroll down
      elif ch == curses.KEY_DOWN:
        if not singlescroll or leftscroll:
          if lastheight < len(lhs):
            if lpos[0] < len(lhs) - lastheight + 1: lpos[0] += 1
        if not singlescroll or not leftscroll:
          if lastheight < len(rhs):
            if rpos[0] < len(rhs) - lastheight + 1: rpos[0] += 1
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
            if lpos[1] < self.lwidth - lastwidth//2 + 2 - paneshmt:
              lpos[1] += 1
        if not singlescroll or not leftscroll:
          if lastwidth//2 - 2 < self.rwidth:
            if rpos[1] < self.rwidth - lastwidth//2 + 2 + paneshmt:
              rpos[1] += 1
      else:
        # If we didn't change the pos then don't repaint
        repaint = False
      if repaint: lastheight, lastwidth = self.draw(lhs, lpos,
                                                    rhs, rpos,
                                                    dohighlight, paneshmt)
      ch = self.stdscr.getch()

  '''
  showmenu()

    This method is used to print a text menu
  '''
  def showmenu(self,
                title='', body=[], err=None, choices=[],
                infobox=False, curs=0):
    titlecolor = curses.color_pair(2) | curses.A_BOLD
    itemcolor = curses.color_pair(1)
    activecolor = curses.color_pair(1) | curses.A_BOLD
    hpos = 0
    topline = 0
    while True:
      height, width = self.stdscr.getmaxyx()
      # clear the screen
      self.stdscr.erase()
      self.stdscr.addstr(0, 0, title, titlecolor)
      linenum = 1
      for section in body:
        for line in section:
          linenum += 1
          self.stdscr.addstr(linenum, 4, line, itemcolor)
        linenum += 1
      linenum += 1
      if err:
        self.stdscr.addstr(linenum, 4, err, curses.color_pair(3) | curses.A_BOLD)
        linenum += 2
      actualtop = linenum
      for i, line in enumerate(choices):
        if linenum == height: break
        if i >= topline:
          color = activecolor if i == hpos else itemcolor
          self.stdscr.addstr(linenum, 4, line, color)
          linenum += 1
      curses.curs_set(curs)
      self.stdscr.refresh()
      ch = self.stdscr.getch()
      curses.curs_set(0)
      if infobox: return
      elif ch == curses.KEY_HOME:
        hpos = 0
        topline = 0
      elif ch == curses.KEY_END:
        if actualtop + len(choices) > height:
          topline = len(choices) - height + actualtop
          hpos = len(choices) - 1
      elif ch == curses.KEY_UP:
        if hpos > 0: hpos -= 1
        if actualtop + hpos - topline < actualtop:
          topline -= 1
      elif ch == curses.KEY_DOWN:
        if hpos < len(choices) - 1: hpos += 1
        if actualtop + hpos - topline == height:
          topline += 1
      elif ch == curses.KEY_PPAGE and hpos > 0:
        hpos -= 4
        if hpos - topline < 0:
          topline = hpos
        if hpos < 0:
          hpos = 0
          topline = 0
      elif ch == curses.KEY_NPAGE:
        hpos += 4
        if hpos >= len(choices) - 1: hpos = len(choices) - 1
        if actualtop + hpos - topline >= height:
          topline += actualtop + hpos - topline - height + 1
      elif ch in [curses.KEY_ENTER, 10, 13]: return hpos

  '''
  filemenu()

    This method is used to print a file selection menu
  '''
  def filemenu(self, title=''):
    cwd = os.getcwd()
    path = cwd
    error = None
    while True:
      names = ['../'] if path != '/' else []
      names += [name for name in os.listdir(path)]
      body = [['Select a text file', '', 'Path: ' + path]]
      ch = self.showmenu(title=title, body = body, err = error, choices = names)
      if error:
        error = None
      if names[ch] == '../' or os.path.isdir(path+'/'+names[ch]):
        if names[ch] == '../':
          path = '/'.join(path.split('/')[:-1])
          if path == '': path = '/'
        elif path == '/': path += names[ch]
        elif names[ch] == cwd: path = cwd
        else:
          path += '/'+names[ch]
        if not os.access(path, os.R_OK):
          error = 'Error reading directory \"' + path + '\"'
          path = cwd
      else:
        try:
          with open(path+'/'+names[ch]) as infile:
            contents = infile.readlines()
            return contents
        except:
          error = 'Error opening \"' + path + '/' + names[ch] + '\"'
  '''
  commands()

    Print command information
  '''
  def commands(self):
    title = 'DiffWindow - a Python curses script to compare 2 text files'
    controls = [['Commands available while the diff view is active:'],
                ['Quit:                              escape, q, Q',
                  'Toggle match highlighting:         d, D, h, H',
                  'Toggle left/right pane lock:       space',
                  'Toggle left/right pane scrolling:  tab',
                  'Move pane separator left/right:    +/-',
                  'Reset pane separator shift    :    =']]
    choices = ['Press the any key to return to the main menu . . . ']
    self.showmenu(title=title,
                  body=controls,
                  choices=choices,
                  infobox=True,
                  curs=2)

  '''
  mainmenu()

    This is the main menu for the menu-driven interface
  '''
  def mainmenu(self):
    # confirm class usage
    try:
      if not self.havescr: self.initscr()
    except AttributeError:
      if self.unsafe: self.initscr()
      else:
        raise AssertionError('unsafe is not true and curses not initialized')
    title = 'DiffWindow - a Python curses script to compare 2 text files'
    body = [['Copyright (C) 2022 Chase Phelps',
              'Provided under the GNU GPL v3 license'],
            ['Choose an option from the menu below:']]
    choices = ['Select the left-hand side file',
                'Select the right-hand side file',
                'Show the diff between the files',
                'Show available commands for diff view',
                'Quit']
    legend = ['lhs','rhs','diff','commands','quit']
    ch = -1
    error = None
    lhs, rhs = None, None
    while ch != choices.index('Quit'):
      ch = self.showmenu(title=title, body=body, err=error, choices=choices)
      if error:
        error=None
      if legend[ch] == 'lhs':
        lhs = self.filemenu()
      elif legend[ch] == 'rhs':
        rhs = self.filemenu()
      elif legend[ch] == 'diff':
        if not lhs or not rhs:
          error = 'Left- and Right- side files must be selected first!'
        else:
          self.showdiff(lhs, rhs)
      elif legend[ch] == 'commands':
        self.commands()

'''
When ran as a script will diff 2 files
'''
if __name__ == '__main__':
  if len(sys.argv) == 3:
    lhs, rhs = [], []
    with open(sys.argv[1]) as infile:
      lhs = infile.readlines()
    with open(sys.argv[2]) as infile:
      rhs = infile.readlines()
    # intended usage
    with DiffWindow() as win:
      win.showdiff(lhs, rhs)
  else:
    with DiffWindow() as win:
      win.mainmenu()
  # class usage
  #win = DiffWindow(unsafe=True)
  #win.initscr() # optional, called automatically in showdiff if unsafe=True
  #win.showdiff(lhs, rhs)
  #win.stopscr() # called in del if initscr has been called
