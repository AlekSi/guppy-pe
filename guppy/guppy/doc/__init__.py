# -*- coding: utf-8 -*-
#._cv_part guppy.doc

# The prettyPrintHTML Code is adapted from:
# http://www.bazza.com/~eaganj/weblog/2006/04/04/printing-html-as-text-in-python-with-unicode/

import guppy
import os

import codecs
import cStringIO
import formatter
import htmlentitydefs
import htmllib

from htmllib import HTMLParser

thisdir = os.path.dirname(__file__)

def utf8StringIO():
    sio = cStringIO.StringIO()
    # cStringIO doesn't like Unicode, so wrap with a utf8 encoder/decoder.
    encoder, decoder, reader, writer = codecs.lookup('utf8')
    return codecs.StreamReaderWriter(sio, reader, writer, 'replace')

class HelpTextWriter(formatter.DumbWriter):
    def reset(self):
        formatter.DumbWriter.reset(self)
        self.margin = 0

    def new_margin(self, tag, level):
        #print >>self.file, "new_margin(%s, %d)" % (`margin`, level)
        self.margin = level*4

    def indento_margin(self):
        if self.col < self.margin:
            self.file.write(' '*(self.margin-self.col))
            self.col = self.margin

    def _send_literal_data(self, data):
        rows = data.split('\n')
        self.file.write(data)
        i = data.rfind('\n')
        if i >= 0:
            self.col = 0
            data = data[i+1:]
        data = data.expandtabs()
        self.col = self.col + len(data)
        self.atbreak = 0

    def send_flowing_data(self, data):
        if not data: return
        self.indento_margin()
        atbreak = self.atbreak or data[0].isspace()
        col = self.col
        maxcol = self.maxcol
        write = self.file.write
        for word in data.split():
            if atbreak:
                if col + len(word) >= maxcol:
                    self.file.write('\n'+' '*self.margin)
                    col = self.margin
                else:
                    write(' ')
                    col = col + 1
            write(word)
            col = col + len(word)
            atbreak = 1
        assert col >= self.margin
        self.col = col
        self.atbreak = data[-1].isspace()

class HelpTextHTMLParser(HTMLParser):
    " HTMLParser tailored to handle help text and can handle unicode charrefs"

    entitydefs = dict([ (k, unichr(v)) for k, v in htmlentitydefs.name2codepoint.items() ])

    def reset(self):
        HTMLParser.reset(self)
        self.index2href = []
        self.href2index = {}
        self.data2href = {}

    def handle_charref(self, name):
        "Override builtin version to return unicode instead of binary strings for 8-bit chars."
        try:
            n = int(name)
        except ValueError:
            self.unknown_charref(name)
            return
        if not 0 <= n <= 255:
            self.unknown_charref(name)
            return
        if 0 <= n <= 127:
            self.handle_data(chr(n))
        else:
            self.handle_data(unichr(n))
            
    # --- Hooks for anchors

    def anchor_bgn(self, href, name, type):
        """This method is called at the start of an anchor region.

        The arguments correspond to the attributes of the <A> tag with
        the same names.  The implementation maintains a dictionary of
        hyperlinks (defined by the HREF attribute for <A> tags) within
        the document.  The dict of hyperlinks is available as the data
        attribute anchordict. It also keeps a list of unique hyperlinks.

        """
        self.anchor = (href, name, type)
        if href:
            self.save_bgn()

    def anchor_end(self):
        """This method is called at the end of an anchor region.

        The implementation adds a textual footnote marker using an
        index into the list of hyperlinks created by the anchor_bgn()method.

        """
        href, name, type = self.anchor
        if href:
            data = self.save_end()
            self.handle_data(data)
            data = data.strip()
            if href in self.href2index:
                index = self.href2index[href]
            else:
                index = len(self.index2href)
                self.href2index[href] = index
                self.index2href.append(href)
            self.handle_data("[%d]" % index)
            
            if data in self.data2href:
                if self.data2href[data] != href:
                    raise Exception, "Same data: '%s' with different href's: '%s','%s'"%(
                        data, href, self.data2href[data])
            else:
                self.data2href[data] = href
        self.anchor = None

    # --- Headings

    def start_hx(self, level, attrs):
        if not (self.list_stack and self.list_stack[-1][0] == 'dd'):
            self.formatter.end_paragraph(1)
        else:
            self.formatter.end_paragraph(0)
        self.formatter.push_font(('h%d'%level, 0, 1, 0))

    def start_h1(self, attrs):
        self.start_hx(1, attrs)

    def start_h2(self, attrs):
        self.start_hx(2, attrs)

    def start_h3(self, attrs):
        self.start_hx(3, attrs)

    def start_h4(self, attrs):
        self.start_hx(4, attrs)

    def start_h5(self, attrs):
        self.start_hx(5, attrs)

    def start_h6(self, attrs):
        self.start_hx(6, attrs)

    def end_hx(self):
        self.formatter.end_paragraph(0)
        self.formatter.pop_font()

    end_h1 = end_h2 = end_h3 = end_h4 = end_h5 = end_h6 = end_hx

    # --- List Elements

    def start_dl(self, attrs):
        self.formatter.end_paragraph(0)
        self.list_stack.append(['dl', '', 0])

class HelpHandler:
    def __init__(self, mod, top):
        self.mod = mod
        self.top = top
        self.output_buffer = self.mod._parent.etc.OutputHandling.output_buffer()
        self.text

    def get_more_index(self, firstindex):
        return firstindex+self.mod.pagerows

    def ppob(self, ob, index):
        text = self.text
        splitext = text.split('\n')
        nextindex = index+self.mod.pagerows
        pst = splitext [index:nextindex]
        print >>ob, '\n'.join(pst)
        if nextindex < len(splitext):
            numore = len(splitext) - nextindex
            if numore == 1:
                pst.extend(splitext[-1:])
            else:
                print >>ob, \
"<%d more rows. Type e.g. '_.more' for more or '_.help' for help on help.>" \
		%numore
        self.nextindex = nextindex
    
    def prettyPrintHTML(self, html):
        " Strip HTML formatting to produce plain text suitable for printing. "
        utf8io = utf8StringIO()
        writer = HelpTextWriter(utf8io)
        prettifier = formatter.AbstractFormatter(writer)
        self.parser = HelpTextHTMLParser(prettifier)
        parser = self.parser
        parser.feed(html)
        parser.close()
        utf8io.seek(0)
        result = utf8io.read()
        utf8io.close()
        return result #.lstrip()

    def _get_text(self):
        text = ''
        if self.top.webarg:
            text += "Web doc page: %s\n"%self.top.webarg
        if self.top.textarg:
            text += self.top.textarg
        if self.top.filenamearg:
            text +=  self.prettyPrintHTML(
                open(os.path.join(thisdir,self.top.filenamearg)).read())
        self.text = text
        return text

    text = property(fget=_get_text)

class Help:
    """\
Help class
"""
    _gslspec_ = """\


"""

    def __init__(self, mod=None, web=None,text=None, filename=None):

        if mod is not None:
            self.mod = mod
            # Otherwise generate it when needed via _get_mod
        self.webarg = web
        self.filenamearg = filename
        self.textarg = text

    def _get_read(self):
        print self
        x=raw_input()

    def _getattr__(self, attr):
        hh = self.handler
        ad = hh.parser.anchordict
        inv = {}
        if attr in ad:
            return ad[attr]
        raise AttributeError, attr

    def __getitem__(self, idx):
        return self.handler.parser.index2href[idx]

    def __repr__(self):
        hh = self.handler
        mp = self.mod._root.guppy.etc.OutputHandling.basic_more_printer(
            self, hh, 0)
        r = repr(mp)
        self.nextindex = hh.nextindex
        return r

    def _get_help(self):
        return Help(text=self.__doc__)

    def _get_handler(self):
        return HelpHandler(self.mod, self)

    def _get_mod(self):
        mod = guppy.Root().guppy.doc
        return mod

    def _get_more(self):
        mp = self.mod._root.guppy.etc.OutputHandling.basic_more_printer(
            self, self.handler, self.nextindex)
        return mp
    
    def go(self, name):
        href = self.handler.parser.data2href[name]
        return href

    handler = property(fget=_get_handler)
    help = property(fget=_get_help)
    mod = property(fget=_get_mod)
    more = property(fget=_get_more)
    read = property(fget=_get_read)


a=3

class X:
    def __repr__(self):
        return 'å'

print 'hello!', a

class _GLUECLAMP_:
    pagerows=20
    def Help(self, *args, **kwds):
        return Help(self, *args, **kwds)
    
        
