#._cv_part guppy

'''\
Top level package of the Guppy system.

What is exported is the following methods:

hpy()	Create an object that provides a Heapy entry point.
Root()	Create an object that provides a top level entry point.

'''

__all__ = ('hpy', 'Root')

import guppy.etc.Compat		# Do one-time compatibility adjustments
from guppy.etc.Glue import Root	# Get main Guppy entry point

from guppy.ihelp import Help
help = Help(filename='./help/guppy.html')

def __str__(self):
    return 'guppy module'

def hpy(ht = None):
    """\
    Main entry point to the Heapy system.
    Returns an object that provides a session context and will import
    required modules on demand. Some commononly used methods are:

    .heap() 		get a view of the current reachable heap
    .iso(obj..) 	get information about specific objects 
    
    The optional argument, useful for debugging heapy itself, is:

        ht     an alternative hiding tag

"""
    r = Root()
    if ht is not None:
	r.guppy.heapy.View._hiding_tag_ = ht
    return r.guppy.heapy.Use

