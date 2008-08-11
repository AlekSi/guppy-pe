# -*- coding: utf-8 -*-
#._cv_part guppy.doc

# The prettyPrintHTML Code is adapted from:
# http://www.bazza.com/~eaganj/weblog/2006/04/04/printing-html-as-text-in-python-with-unicode/

import guppy
import os
import new

import codecs
import cStringIO
import formatter
import htmlentitydefs
import htmllib
import urllib2 as urllib

from htmllib import HTMLParser

THISDIR = os.path.dirname(__file__)

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
        self.data2hrefs = {}
        self.name2textpos = {}

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

        if name:
            self.name2textpos[name] = self.formatter.writer.file.tell()

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
            
            self.data2hrefs.setdefault(data,{})[index]=href

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

class Document:
    ''' Abstracts a document, derived from one HTML file '''
    def __init__(self, mod, url):
        self.mod = mod
        self.url = url
        self.reset()

    def getdoc(self, hrefdata=None, url=None, idx=None):
        try:
            hrefs = self.doc.hrefsbydata(name)
        except KeyError:
            print "Help text has no link %r"%name
            self.print_available_links()
        
        return hrefs

    def hrefsbydata(self, data):
        return self.parser.data2hrefs[data]

    def hrefbyindex(self, idx):
        return self.parser.index2href[idx]

    def urlbyindex(self, idx):
        return self.urlbyhref(self.hrefbyindex(idx))

    def urlsbydata(self, data):
        return dict([(key, self.urlbyhref(href)) for (key, href) in
                     self.hrefsbydata(data).items()])

    def urlbyhref(self, href):
        if href.startswith('#'):
            href = self.url+href
        return href
        
    def reset(self):
        html = self.readhtml()
        self.text = self.prettyPrintHTML(html)

    def readhtml(self):
        return urllib.urlopen(self.url).read()

    def prettyPrintHTML(self, html):
        " Strip HTML formatting to produce plain text suitable for printing. "
        utf8io = utf8StringIO()
        writer = HelpTextWriter(utf8io)
        prettifier = formatter.AbstractFormatter(writer)
        self.parser = parser = HelpTextHTMLParser(prettifier)
        parser.feed(html)
        parser.close()


        utf8io.seek(0)
        result = utf8io.read()
        utf8io.close()
        return result #.lstrip()

class Subject:
    def __init__(self, mod, doc, fragment):
        self.mod = mod
        self.doc = doc
        self.fragment = fragment
        text = doc.text
        if fragment:
            text = text[doc.parser.name2textpos[fragment]:]
            fragment = '#'+fragment
        self.text = text
        self.header = '%s%s'%(os.path.basename(doc.url),fragment)
                        

class HelpHandler:
    ''' Handles a particular help strategy
    '''

    def get_more_index(self, firstindex):
        return firstindex+self.mod.pagerows

    def ppob(self, ob, index):
        text = self.get_text()
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
    
    def get_text(self):
        text = self.subject.text
        return text

class Help(HelpHandler):
    """\
Help class
"""
    _gslspec_ = """\


"""
    _all_ = ('back', 'down', 'forw', 'more', 'og', 'pop',
             'ret', 'up', 'top')

    def __init__(self, tab, url, startindex=0):
        self.tab = tab
        mod = tab.mod
        self.mod = mod
        self.url = url
        self.startindex = startindex
        self.subject = mod.getsubject(url)
        self.append_to_history()
        self.notification = None

    def __getattr__(self, attr):
        while 1:
            if attr.startswith('go'):
                return self.go(attr[2:])
            elif attr.startswith('tab'):
                return self.seltab(attr[3:])
            else:
                possibs = []
                for a in self._all_:
                    if a.startswith(attr):
                        possibs.append(a)
                print 'possibs', possibs
                if len(possibs) == 1:
                    return getattr(self,possibs[0])
                if len(possibs) > 1:
                    return self.notify('Which did you mean: %s'%possibs)
                return self.notify('No such attribute: %r'%attr)

    def __getitem__(self, idx):
        return self.go(str(idx))

    def __repr__(self):
        if self.notification is not None:
            r = '*** %s ***' % self.notification
            self.notification = None
            return r
	ob = self.mod.output_buffer()
        print >>ob, '--- %s ---'%self.header
        
	self.ppob(ob, self.startindex)
	r = ob.getvalue().rstrip()
        return r

    def _get_back(self):
        if (self.history_index == 0):
            return self.notify('At first help subject in session. (Try .less if you did .more)')
        else:
            return self.tab.history[self.history_index-1]

    def _get_forw(self):
        if (self.history_index >= len(self.tab.history)-1):
            #return self.notify('No forward subject. (Try also .more .)')
            return self.more
        else:
            return self.tab.history[self.history_index+1]

    def _get_header(self):
        return 'tab%s: %s [+%d]'%(
            self.tab.name, self.subject.header,self.startindex)

    def _get_help(self):
        return Help(text=self.__doc__)

    def _get_less(self):
        if self.startindex == 0:
            return self.notify('No previous rows in subject.')

    def _get_more(self):
        del self.tab.history[self.history_index+1:]
        repr(self)	# Just to calculate nextindex ...
        h = self.copy(startindex = self.nextindex)
        h.append_to_history()
        return h

    def _get_ret(self):
        try:
            return self._ret
        except AttributeError:
            return self.notify("No subject to return to.")

    def _get_tabs(self):
        return self.notify(str(self.mod.tabs))

    def _get_top(self):
        return self

    def append_to_history(self):
        self.history_index = len(self.tab.history)
        self.tab.history.append(self)

    def copy(self, **kwds):
        n = new.instance(self.__class__)
        n.__dict__.update(self.__dict__)
        n.__dict__.update(kwds)
        return n

    def notify(self, message):
        self.notification = message
        return self

    def urlbydata(self, name):
        while 1:
            try:
                urls = self.subject.doc.urlsbydata(name)
            except KeyError:
                print "Help text has no link %r"%name
                self.print_available_links()
            else:
                if len(urls) == 1:
                    return urls.values()[0]
                print "Ambiguos name: ", urls

    def urlbyindex(self, index):
        try:
            url = self.subject.doc.urlbyindex(index)
        except KeyError:
            print "Help text has no link %r"%index
        return url

    def urlby(self, name):
        if name.isdigit():
            url = self.urlbyindex(int(name))
        else:
            url = self.urlbydata(name)
        return url

    def go(self, name):
        url = self.urlby(name)
        del self.tab.history[self.history_index+1:]
        h = self.copy(url=url, subject = self.mod.getsubject(url),
                      _ret=self,
                      startindex=0)
        h.append_to_history()
        return h

    def seltab(self, name):
        if name in self.mod.tabs:
            h = self.mod.tabs[name].history[-1]
        else:
            h = self.copy()
            h.tab = Tab(self.mod, name)
            h.append_to_history()
        h.notify(h.header)
        return h
        

    back = up = property(fget=_get_back)
    forw = down = property(fget=_get_forw)
    header = property(fget=_get_header)
    help = property(fget=_get_help)
    less = property(fget=_get_less)
    more = property(fget=_get_more)
    ret = pop = og = property(fget=_get_ret)
    tabs = property(fget=_get_tabs)
    top = property(fget=_get_top)

class Tab:
    def __init__(self, mod, name):
        self.mod = mod
        self.mod.tabs[name] = self
        self.name = name
        self.history = []

    def __repr__(self):
        return '\n'.join([x.header for x in self.history])

class StaticHelp:
    ''' For use in modules and classes to minimize memory impact.
        Does not cache anything but creates a (dynamic) Help instance
        each time it is used, which it acts as a proxy to.
    '''

    def __init__(self, *args, **kwds):
        self._args = args
        self._kwds = kwds

    def __getattr__(self, attr):
        mod = guppy.Root().guppy.doc

        dynhelp = mod.Help(*self._args, **self._kwds)
        return getattr(dynhelp, attr)

class _GLUECLAMP_:
    #'public'

    pagerows=14		# Default number of rows to show at a time

    def Help(self, *args, **kwds):
        tab = Tab(self, str(len(self.tabs)))
        return Help(tab, *args, **kwds)
    
    #'private'
    
    _chgable_=('pagerows',)
    _imports_ = (
        '_root.urlparse:urldefrag',
        '_root.guppy.etc.OutputHandling:output_buffer',
        )
    
    def _get_tabs(self):
        return {}
    
    def _get_url2doc(self):
        return {}
    
    def fixurl(self, url):
        if '://' not in url:
            if not os.path.isabs(url):
                url = os.path.join(THISDIR,url)
            url = 'file://'+url
        return url

    def getdoc(self, url):
        if url in self.url2doc:
            return self.url2doc[url]
        doc = Document(self, url)
        self.url2doc[url] = doc
        return doc

    def getsubject(self, url):
        url = self.fixurl(url)
        url, frag = self.urldefrag(url)
        doc = self.getdoc(url)
        return self.Subject(self, doc, frag)

    def help_instance(self, inst):
        url = inst._help_url_
        return self.Help(url)
