#! /usr/bin/env python3

import curses, os, re, sys
from string import printable

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

# Menu functions could be in their own file, say displays.py, and used like:
#sys.dont_write_bytecode = True # don't make the __pycache__ folder
#from displays import showmenu, filemenu, drawsplitpane

'''
showmenu(scr, title, body, err, choices, infobox, curs, hpos)

  This method is used to print a text menu using the screen scr

  The title is drawn on the first line
  An empty line separates the title from the body
  The body is a list of lists of strings
  Each is separated by a line
  The error, if present, is then printed in error color
  The remaining lines are "choice" lines which can be scrolled
  The current selection at hpos will be highlighted

  The user makes their selection with navigation keys
  When enter is pressed, the corresponding index of choices is returned
  If escape, q, or Q is pressed, None is returned

  If infobox is True this method will return on the first keypress

  curses.curs_set is set with the curs parameter
    0 is hidden
    1 is (possibly) an underscore/line
    2 is (possibly) a block
'''
def showmenu(scr,
              title='', body=[[]], err=None, choices=[],
              infobox=False, curs=0, topline=0, hpos=0):
  if hpos < topline: hpos = topline
  # track width
  maxwidth = len(title)
  for section in body:
    for line in section: maxwidth = max(len(line),maxwidth)
  errorlen = 1
  if type(err) is str: maxwidth = max(len(err),maxwidth)
  elif type(err) is list:
    errorlen = len(err)
    for e in err: maxwidth = max(len(e),maxwidth)
  for line in choices: maxwidth = max(len(line),maxwidth)
  # set colors to be used
  titlecolor = curses.color_pair(2) | curses.A_BOLD
  itemcolor = curses.color_pair(1)
  activecolor = curses.color_pair(1) | curses.A_BOLD
  errorcolor = curses.color_pair(3) | curses.A_BOLD
  # when the counter hits zero make the error disappear
  errorcounter = None
  while True:
    if err and errorcounter == 0:
      topline -= errorlen + 1
      if topline < 0: topline = 0
      err = None
    # get the current dimensions
    height, width = scr.getmaxyx()
    # get side buffer
    lshift = 0
    if maxwidth < width: lshift = (width-maxwidth)//2
    # clear the screen
    scr.erase()
    # add the title
    scr.insstr(0, 0+lshift, title, titlecolor)
    # track the line number we are printing to
    linenum = 1
    for section in body:
      # print all lines in a section of the body
      for line in section:
        linenum += 1
        scr.insstr(linenum, 4+lshift, line, itemcolor)
      # separate body sections by a newline
      linenum += 1
    # separate body from remainder with another newline
    linenum += 1
    if err:
      # print an error message if we have one, add 2 lines
      if type(err) is list:
        for e in err:
          if e == '': continue
          scr.insstr(linenum, 4+lshift, e, errorcolor)
          linenum += 1
        linenum -= 1
      else:
        scr.insstr(linenum, 4+lshift, err, errorcolor)
      linenum += 2
      if errorcounter is None:
        errorcounter = 5
        if height-linenum < len(choices):
          topline += errorlen + 1
          # if the error pushes hpos out of sight
          if topline > hpos: topline = hpos
      else:
        errorcounter -= 1
    # track the actual top line of the choices
    actualtop = linenum
    # i is zero indexed matching hpos
    for i, line in enumerate(choices):
      # we cannot go beyond height if choices is a long list
      if linenum == height: break
      # print this line
      if i >= topline:
        # set the color to active if this is our highlight position
        color = activecolor if i == hpos else itemcolor
        scr.insstr(linenum, 4+lshift, line, color)
        linenum += 1
    # set the cursor according to the argument and refresh the screen
    if curs != 0:
      cursorcol = 4 + lshift + len(choices[hpos])
      if cursorcol < width:
        scr.move(actualtop + hpos - topline, cursorcol)
        curses.curs_set(curs)
    scr.refresh()
    # get our response, reset the cursor and process the response
    ch = scr.getch()
    curses.curs_set(0)
    # allow to return without making a selection:
    # escape = 27, 'Q'=81, 'q'=113
    if ch in [27, 81, 113]: return None, None
    # this argument indicates we return immediately on a keypress
    if infobox: return
    # go to the top
    elif ch == curses.KEY_HOME:
      hpos = 0
      topline = 0
    # go to the bottom
    elif ch == curses.KEY_END:
      if actualtop + len(choices) > height:
        topline = len(choices) - height + actualtop
        hpos = len(choices) - 1
    # go up
    elif ch == curses.KEY_UP:
      if hpos > 0:
        hpos -= 1
        if actualtop + hpos - topline < actualtop: topline -= 1
    # go down
    elif ch == curses.KEY_DOWN:
      if hpos < len(choices) - 1:
        hpos += 1
        if actualtop + hpos - topline == height: topline += 1
    # jump up
    elif ch == curses.KEY_PPAGE and hpos > 0:
      hpos -= 4
      if hpos - topline < 0: topline = hpos
      if hpos < 0:
        hpos = 0
        topline = 0
    # jump down
    elif ch == curses.KEY_NPAGE:
      hpos += 4
      if hpos >= len(choices) - 1: hpos = len(choices) - 1
      if actualtop + hpos - topline >= height:
        topline += actualtop + hpos - topline - height + 1
    # on enter we return our highlighted position
    elif ch in [curses.KEY_ENTER, 10, 13]: return topline, hpos

'''
filemenu(scr, title)

  This method is used to print a file selection menu on scr
  The navigation begins from the current working directory
  The choices are the contents of the currently selected directory
  A file opened must be a text file

  Returns -> the file.readlines() list (or None if cancelled)
'''
def filemenu(scr, title=''):
  # the path starts at the current working directory
  path = os.getcwd()
  error = None
  body = [['Select a text file'], ['Path: ' + path]]
  topline = 0
  ch = 0
  while True:
    # give an option to go up a level unless we are at the root
    if path == '': path = '/'
    names = ['../'] if path != '/' else []
    # add the contents of the directory
    names += [name+'/' for name in os.listdir(path) \
                        if os.path.isdir(path+'/'+name)]
    names += [name for name in os.listdir(path) \
                        if os.path.isfile(path+'/'+name)]
    names.sort()
    # get the response
    topline, ch = showmenu(scr, title=title, body=body, err=error,
                            choices=names, topline=topline, hpos=ch)
    # allow to return without opening a file:
    if ch is None: return None, None
    # reset the error message
    error = None
    # if we selected to go up or our selection is a subdirectory
    if names[ch][-1] == '/':
      # if we chose to go up remove the last directory from the path
      if names[ch] == '../':
        path = '/'.join(path.split('/')[:-1])
        # the root will become an empty string
        if path == '': path = '/'
      # we chose a directory from our path
      else:
        # test to see if we can get a list of the directory contents
        names[ch] = names[ch][:-1]
        testpath = path + names[ch] if path == '/' else path + '/' + names[ch]
        try: os.listdir(testpath)
        except Exception as e:
          # if we can't read the directory set an error string and continue
          error = str(e).split(':')
          continue
        # if we could read the directory set the path
        path = testpath
      # update the path in the body text
      body[-1][-1] = 'Path: ' + path
      ch = 0
      topline = 0
    # our selection was a file
    else:
      # try to read the file
      try:
        if path == '/': path = ''
        # reading the file will fail without permissions
        # or if the file is definitely not a text file
        # (some binary files will pass here and throw an exception if used)
        with open(path+'/'+names[ch]) as infile:
          contents = infile.readlines()
          if not contents:
            error = 'File \"' + names[ch] + '\" appears empty'
          for line in contents:
            if any(c not in printable and not isinstance(c, str) for c in line):
              error = 'File \"' + names[ch] + '\" not printable'
              break
          if not error: return contents, names[ch]
      except Exception as e:
        error = str(e).split(':')

'''
drawsplitpane(scr, lhs, lpos, rhs, rpos, highlight, paneshmt, halfgap)

  This method draws a split pane view
  lhs and rhs are lists of strings
  lpos and rpos determines which row/col is the top left of each pane
  The screen is divided vertically into 2 segments with a gap of halfgap*2
  The screen is cleared, strings added to screen, then refreshed
  Returns the current height, width
'''
def drawsplitpane(scr, lhs, lpos, rhs, rpos, highlight, paneshmt=0, halfgap=2):
  infocolor = curses.color_pair(2) | curses.A_BOLD
  # clear the screen
  scr.erase()
  # the current height and width (will change if window is resized)
  height, width = scr.getmaxyx()
  # paneshmt can be negative or positive for left/right
  middle = width//2 + paneshmt
  # if the middle is shifted left or right
  if paneshmt != 0:
    # if the rhs was shifted out of view
    if middle >= width - halfgap:
      scr.insstr(0, 1, 'left', infocolor)
      rstart = width
      lstop = width + lpos[1]
    # if the lhs was shifted out of view
    elif middle <= halfgap:
      scr.insstr(0, width-6, 'right', infocolor)
      rstart = 0
      lstop = lpos[1]
    # otherwise the boundary is still in the middle
    else:
      scr.insstr(0, 1, 'left', infocolor)
      scr.insstr(0, width-6, 'right', infocolor)
      rstart = middle + halfgap
      lstop = middle - halfgap + lpos[1]
  else:
    rstart = middle + halfgap
    lstop = middle - halfgap + lpos[1]
    scr.insstr(0, 1, 'left', infocolor)
    scr.insstr(0, width-11, 'right', infocolor)
  rstop = width - rstart + rpos[1]
  # the default color is standard color
  color = curses.color_pair(0)
  # add lines
  for i in range(1, height):
    if highlight:
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
        scr.insstr(i, 0, lhs[lpos[0]+i][lpos[1]:lstop], color)
      elif i+lpos[0] == len(lhs):
        scr.insstr(i, 1, 'END', infocolor)
    # draw rhs if we have a row here
    if rstop != rpos[1]:
      if i+rpos[0] < len(rhs):
        scr.insstr(i, rstart, rhs[rpos[0]+i][rpos[1]:rstop], color)
      elif i+rpos[0] == len(rhs):
        scr.insstr(i, width-4, 'END', infocolor)
  scr.refresh()
  return height, width

'''
  DiffWindow
  ___________
  An implementation of curses for side-by-side file comparison

  A class to be used in the manner "with DiffWindow() as win:"
    this usage keeps curses from messing up the terminal on exceptions/etc.

  Alternate usage, instantiating a class, is win = DiffWindow(unsafe=True)
    (the method which initializes curses is initscr)
    (the method which restores the shell is stopscr)
    initscr will be called automatically when needed if unsafe=True
    stopscr will be called on __del__

  The "main" method, showdiff, takes 2 lists of strings like:
    lhs = [line.rstrip() for line in lhsfile.readlines()]
    rhs = [line.rstrip() for line in rhsfile.readlines()]

  Alternatively, this script can run as a menu-driven script:
    with DiffWindow() as win:
      win.mainmenu()
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
'''

class DiffWindow:
  '''
  __init__

    Set unsafe flag to allow usage without enter/exit
    The intended usage is as described above and in the "if name == __main__"
  '''
  def __init__(self, unsafe=False): self.unsafe = unsafe

  '''
  __enter__

    We init curses, get a screen, and set options
    Returns self for use with the listdiff() function
  '''
  def __enter__(self): return self.initscr()

  '''
  __exit__

    We teardown curses and return the terminal to normal operation
  '''
  def __exit__(self, type, value, traceback): self.stopscr()

  '''
  __del__

    Ensure curses has been town down
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
    try:
      if self.havescr: return
    except AttributeError: pass
    self.havescr = True
    # get the std screen
    self.stdscr = curses.initscr()
    # enable color output
    curses.start_color()
    # we can use pair numbers from 1 ... (0 is standard)
    # COLOR_ BLACK, BLUE, CYAN, GREEN, MAGENTA, RED, WHITE, YELLOW
    # this will be for standard text
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    # this will be for title text
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)
    # this will be error text
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
    try:
      if self.havescr:
        self.havescr = False
        curses.nocbreak()
        self.stdscr.keypad(False)
        curses.echo()
        curses.endwin()
    except AttributeError: pass

  '''
  showdiff(lhs, rhs)

    This is the main driver function for the file diff display
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
    # remove empty lines, trailing whitespace, and tabs from lhs / rhs
    lhs = [re.sub('\t','  ',line.rstrip()) for line in lhs \
                                              if line.strip() != '']
    rhs = [re.sub('\t','  ',line.rstrip()) for line in rhs \
                                              if line.strip() != '']
    # get column length for lhs and rhs (max of any element)
    self.lwidth = 0
    for row in lhs: self.lwidth = max(len(row),self.lwidth)
    self.rwidth = 0
    for row in rhs: self.rwidth = max(len(row),self.rwidth)
    # track top left 'coordinate' of the text in the lists
    # the l/rpos is the starting row + col to display
    lpos = [0,0] # lpos[0] is starting row
    rpos = [0,0] # rpos[1] is starting col
    # track the last known height/width as the window could be resized
    lastheight, lastwidth = self.stdscr.getmaxyx()
    # allow independent scrolling
    singlescroll = False
    # side toggle for independent scrolling
    leftscroll = True
    scroll = lambda x: not singlescroll or leftscroll if x=='left' \
                    else not singlescroll or not leftscroll
    # toggle for whether to highlight matching lines
    highlight = True
    # shift amount for pane boundary, division between lhs/rhs views
    paneshmt = 0
    # these chars will quit: escape = 27, 'Q'=81, 'q'=113
    # we'll start at home
    ch = curses.KEY_HOME
    while ch not in [27, 81, 113]:
      middle = lastwidth//2 + paneshmt
      # repaint the screen if we do one of these conditions
      repaint = True
      # the space key to toggle independent scrolling
      if ch == 32: singlescroll = not singlescroll
      # the tab key to toggle whether lhs is active (otherwise rhs)
      elif ch == 9: leftscroll = not leftscroll
      # toggle line match highlight with d, D, h, or H (for diff/highlight)
      elif ch in [68, 72, 100, 104]: highlight = not highlight
      # plus key to shift pane separator right
      elif ch == 43:
        if middle < lastwidth - 2: paneshmt += 1
      # minus key to shift pane separator left
      elif ch == 45:
        if middle > 2: paneshmt -= 1
      # equal key to reset pane shift
      elif ch == 61: paneshmt = 0
      # reset positions
      elif ch == curses.KEY_HOME:
        if scroll('left'): lpos[0] = -1
        if scroll('right'): rpos[0] = -1
      # go to the bottom
      elif ch == curses.KEY_END:
        # fit our maxheight in the last known height
        if scroll('left') and lastheight < len(lhs):
          lpos[0] = len(lhs) - lastheight + 1
        if scroll('right') and lastheight < len(rhs):
          rpos[0] = len(rhs) - lastheight + 1
      # page up
      elif ch == curses.KEY_PPAGE:
        if scroll('left'):
          lpos[0] -= lastheight - 4
          if lpos[0] < 0: lpos[0] = -1
        if scroll('right'):
          rpos[0] -= lastheight - 4
          if rpos[0] < 0: rpos[0] = -1
      # page down
      elif ch == curses.KEY_NPAGE:
        if scroll('left') and lastheight < len(lhs):
          lpos[0] += lastheight - 4
          if lpos[0] > len(lhs) - lastheight:
            lpos[0] = len(lhs) - lastheight + 1
        if scroll('right') and lastheight < len(rhs):
          rpos[0] += lastheight - 4
          if rpos[0] > len(rhs) - lastheight:
            rpos[0] = len(rhs) - lastheight + 1
      # scroll up
      elif ch == curses.KEY_UP:
        if scroll('left') and lpos[0] >= 0: lpos[0] -= 1
        if scroll('right') and rpos[0] >= 0: rpos[0] -= 1
      # scroll down
      elif ch == curses.KEY_DOWN:
        if scroll('left') and lastheight - 2 < len(lhs):
          if lpos[0] < len(lhs) - lastheight + 1: lpos[0] += 1
        if scroll('right') and lastheight - 2 < len(rhs):
          if rpos[0] < len(rhs) - lastheight + 1: rpos[0] += 1
      # scroll left
      elif ch == curses.KEY_LEFT:
        if scroll('left') and lpos[1] > 0:
          lpos[1] -= 1
        if scroll('right') and rpos[1] > 0:
          rpos[1] -= 1
      # scroll right
      elif ch == curses.KEY_RIGHT:
        if scroll('left') and middle > 2:
          if self.lwidth - lpos[1] > middle - 2: lpos[1] += 1
        if scroll('right') and middle < lastwidth:
          if self.rwidth - rpos[1] > lastwidth - middle - 2: rpos[1] += 1
      # if we didn't change the pos then don't repaint
      else: repaint = False
      if repaint:
        lastheight, lastwidth = drawsplitpane(self.stdscr,
                                              lhs, lpos, rhs, rpos,
                                              highlight, paneshmt)
      ch = self.stdscr.getch()

  '''
  commands()

    Print command information
  '''
  def commands(self, title=''):
    controls = [['Commands available while the diff view is active:'],
                 ['                            Quit:  escape, q, Q',
                  '       Toggle match highlighting:  d, D, h, H',
                  '     Toggle left/right pane lock:  space',
                  'Toggle left/right pane scrolling:  tab',
                  '  Move pane separator left/right:  +/-',
                  '      Reset pane separator shift:  =']]
    choices = ['Press the any key to return to the main menu . . . ']
    showmenu(self.stdscr, title=title, body=controls,
              choices=choices, infobox=True, curs=2)

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
    # the title for each window
    title = 'DiffWindow - a Python curses script to compare 2 text files'
    # the body text
    body = [['Copyright (C) 2022 Chase Phelps',
              'Licensed under the GNU GPL v3 license'],
            ['Choose an option from the menu below:']]
    # the choices
    choices = ['Select the left-hand side file',
                'Select the right-hand side file',
                'Show the diff between the files',
                'Show available commands for diff view',
                'Quit']
    # a legend of choices to allow more descriptive comparison
    legend = ['lhs','rhs','diff','commands','quit']
    # initialize our variables
    ch = 0
    error = None
    lhs, rhs = None, None
    # while quit is not chosen
    while True:
      # get a choice
      topline, ch = showmenu(self.stdscr, title=title, body=body,
                              err=error, choices=choices, hpos=ch)
      # allow to quit on escape, q, or Q:
      if ch is None: break
      error=None
      # open a file to set lhs
      if legend[ch] == 'lhs':
        ret, name = filemenu(self.stdscr, title=title)
        # didn't have a lhs before and didn't get one
        if lhs is None and ret is None: pass
        # didn't have a lhs before and have one now
        elif lhs is None and ret is not None:
          choices[legend.index('lhs')] += ' (set to \"' + name + '\")'
        # had a filename and don't have one now, remove filename
        elif lhs is not None and ret is None:
          choices[legend.index('lhs')] = \
              choices[legend.index('lhs')].split(' (set to ')[0]
        # had a filename before and (may) have a different one now
        else:
          choices[legend.index('lhs')] = \
              choices[legend.index('lhs')].split(' (set to ')[0]
          choices[legend.index('lhs')] += ' (set to \"' + name + '\")'
        lhs = ret
      # open a file to set rhs
      elif legend[ch] == 'rhs':
        ret, name = filemenu(self.stdscr, title=title)
        # didn't have a rhs before and didn't get one
        if rhs is None and ret is None: pass
        # didn't have a rhs before and have one now
        elif rhs is None and ret is not None:
          choices[legend.index('rhs')] += ' (set to \"' + name + '\")'
        # had a filename and don't have one now, remove filename
        elif rhs is not None and ret is None:
          choices[legend.index('rhs')] = \
              choices[legend.index('rhs')].split(' (set to ')[0]
        # had a filename before and (may) have a different one now
        else:
          choices[legend.index('rhs')] = \
              choices[legend.index('rhs')].split(' (set to ')[0]
          choices[legend.index('rhs')] += ' (set to \"' + name + '\")'
        rhs = ret
      # show the diff of lhs and rhs
      elif legend[ch] == 'diff':
        if not lhs and not rhs:
          error = 'Left- and Right- side files must be selected first!'
        elif not lhs:
          error = 'Left- side file must be selected first!'
        elif not rhs:
          error = 'Right- side file must be selected first!'
        else:
          self.showdiff(lhs, rhs)
      # show the command information
      elif legend[ch] == 'commands':
        self.commands(title=title)
      # quit
      elif legend[ch] == 'quit':
        return

'''
__name__ == __main__
  When len(argv) == 3, attempt to read -> lhs=argv[1], rhs=argv[2]
  Otherwise start the main menu

  Usage of DiffWin class is demonstrated below
'''
if __name__ == '__main__':
  if len(sys.argv) == 3:
    lhs, rhs = [], []
    with open(sys.argv[1]) as infile: lhs = infile.readlines()
    with open(sys.argv[2]) as infile: rhs = infile.readlines()
    with DiffWindow() as win: win.showdiff(lhs, rhs)
  else:
    with DiffWindow() as win: win.mainmenu()
  # class usage
  #win = DiffWindow(unsafe=True)
  #win.initscr() # optional, called automatically in showdiff if unsafe=True
  #win.showdiff(lhs, rhs)
  #win.stopscr() # called in del if initscr has been called

# vim: tabstop=2 shiftwidth=2 expandtab
