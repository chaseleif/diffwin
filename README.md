# DiffWindow

### a Python curses script to compare 2 text files

___

## Example usage from the script:

```
from diffwin import DiffWindow
if __name__ == '__main__':
  if len(sys.argv) == 3:
    lhs, rhs = [], []
    with open(sys.argv[1]) as infile:
      lhs = infile.readlines()
    with open(sys.argv[2]) as infile:
      rhs = infile.readlines()
    with DiffWindow() as win:
      win.showdiff(lhs, rhs)
  else:
    with DiffWindow() as win:
      win.mainmenu()
```

___
## Menu commands:

Navigation:  up, down, left, right, pgup, pgdown, home, end  
Quit/cancel: escape, q, Q  

___
## Diff window commands:

Toggle left and right pane lock:   space  
Toggle left and right pane scroll: tab  
Shift pane separator left/right:   +, -  
Reset pane separator location:     =  
Toggle matching line highlight:    d, D, h, H  

___
## Further information:

Read the comments for further information and examples  

