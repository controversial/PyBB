# PyBB
A Python interface to NodeBB forums.

Implements classes for:
  - Forums
  - Users

I plan to add classes for:
  - Topics
  - Posts

Also tries to implement 'smart' methods for returning data:
  - Return a datetime object for any time-related value

## Example usage

```python
# Get object for omz-software forums
forum = Forum('https://forum.omz-software.com/')
# print forum title
print(forum.title)
# get a forum user and show their profile picture 
u = forum.User('Webmaster4o')
u.image.show()
```
