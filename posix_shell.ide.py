import GPS
from gps_utils.console_process import Console_Process
from gi.repository import Gtk
from setuptools.command import easy_install
import pkg_resources
import os
import cgi
import re
import json
TEST_COLOR = {'PASSED': '#494',
              'FAILED': '#944',
              'PROBLEM': '#944'}

ROOT_DIR = os.path.dirname(__file__)
TS_DIR = './testsuite'


def open_coverage(gcov_file):
    result_xml = ""
    total_child = 0
    total_coverage = 0

    with open(gcov_file, 'rb') as fd:
        result = json.load(fd)

    for source in result:
        total = len(result[source]['lines'])
        covered = len([k for k in result[source]['lines']
                       if result[source]['lines'][k]['status'] ==
                       'COVERED'])

        result_xml += '<File status="VALID" children=' + \
            '"%s" coverage="%s" line_count="%s">\n' % \
            (total,
             total - covered,
             result[source]['line_count'])
        total_child += total
        total_coverage += total - covered

        result_xml += '    <vfs_name>%s</vfs_name>\n' % source

        # sort the lines. necessary ?
        lines = [int(k) for k in result[source]['lines'].keys()]

        for line in sorted(lines):
            l = result[source]['lines'][str(line)]
            # how to interpret negative coverage ?
            if l['coverage'] < 0:
                l['coverage'] = 0 - l['coverage']

            l['line'] = line
            l['contents'] = cgi.escape(l['contents'], quote=True)
            l['contents'] = l['contents'].encode('ascii',
                                                 'xmlcharrefreplace')

            result_xml += '    <Line status="%(status)s" ' % l
            result_xml += 'coverage="%(coverage)s" ' % l
            result_xml += 'number="%(line)s" ' % l
            result_xml += 'contents="%(contents)s" />\n' % l

        result_xml += '</File>\n'

    result_xml = """<?xml version="1.0"?>
    <?xml-stylesheet href='show_coverage.xsl' type='text/xsl'?>
    <Code_Analysis_Tree name="Coverage" >
    <Project status="VALID" name="Posix_Shell" children="%s" coverage="%s">
    %s</Project></Code_Analysis_Tree>""" % \
        (total_child, total_coverage, result_xml)

    # Dump xml file and open the Coverage info
    tmp_file = os.path.join(TS_DIR, 'tmp.xml')

    with open(tmp_file, 'wb') as fd:
        fd.write(result_xml)
    a = GPS.CodeAnalysis.get("Coverage")
    a.clear()
    a.load_from_file(xml=GPS.File(tmp_file))
    a.show_analysis_report()


class GSHCommand(GPS.Process):

    regexp = ".+"

    def __init__(self, command, exit_fun=None):
        self.exit_fun = exit_fun
        GPS.Process.__init__(self,
                             command,
                             on_exit=self.on_exit,
                             show_command=True,
                             regexp=self.regexp,
                             on_match=self.on_match,
                             progress_regexp=" *\(([0-9]*)/([0-9]*)\)",
                             progress_current=1,
                             progress_total=2)

    def on_match(self, matched, unmatched):
        console = GPS.Console("GSH")
        console.write(matched + unmatched + '\n')

    def on_exit(self, status, remaining_output):
        console = GPS.Console("GSH")
        console.write("exit with status: %s\n" % status)
        if status == 0 and self.exit_fun is not None:
            self.exit_fun()


class GSHTestsuite(GSHCommand):

    regexp = "(INFO|ERROR) *:? [^ ]+ *: (PASSED|FAILED|PROBLEM)"

    def __init__(self, command):
        self.report_widget = TestsuiteWidget()
        GSHCommand.__init__(self, command)

    def on_match(self, matched, unmatched):
        GSHCommand.on_match(self, matched, unmatched)
        if re.match(r'(INFO|ERROR):', matched):
            test_name = matched.split(':')[1].strip()
        else:
            m = re.match(r'(INFO|ERROR) *([^ ]*) *: (PASSED|FAILED|PROBLEM)',
                         matched)
            test_name = m.group(2)
        self.report_widget.add_result(test_name)


class GSHActions(object):

    def __init__(self):
        # Menu Run Testsuite with coverage
        self.runtest_action = GPS.Action('gsh_runtest_action')
        self.runtest_action.create(GSHActions.runtest_action,
                                   category="GSH",
                                   description="Run GSH testsuite")
        self.runtest_action.menu("GSH/Run Testsuite")

        # Menu show full coverage
        self.showcov_action = GPS.Action('gsh_showcov_action')
        self.showcov_action.create(GSHActions.showcov_action,
                                   category="GSH",
                                   description="Display full coverage")
        self.showcov_action.menu("GSH/Show Full Coverage")

        # Menu Run Testsuite without coverage
        self.runtestnocov_action = GPS.Action('gsh_runtestnocov_action')
        self.runtestnocov_action.create(GSHActions.runtestnocov_action,
                                        category="GSH",
                                        description="Run GSH testsuite")
        self.runtestnocov_action.menu("GSH/Run Testsuite (no cov)")

        # Menu Build
        self.build_action = GPS.Action('gsh_build_action')
        self.build_action.create(GSHActions.build_action,
                                 category="GSH",
                                 description="Build")
        self.build_action.menu("GSH/Build")

        # Menu Console AdaLua
        self.console_action = GPS.Action('gsh_console_action')
        self.console_action.create(GSHActions.console_action,
                                   category="GSH",
                                   description="Launch AdaLua console")
        self.console_action.menu("GSH/Console AdaLua")

    @classmethod
    def runtest_action(cls):
        GSHTestsuite(
            "python %s/testsuite -j0 -o %s/out --enable-coverage -t %s/tmp" %
            (TS_DIR, TS_DIR, TS_DIR))

    @classmethod
    def showcov_action(cls):

        glob_cov_file = os.path.join('.', 'obj', 'dev', 'global.cov.json')
        print glob_cov_file

        if not os.path.isfile(glob_cov_file):
            console = GPS.Console("GSH")
            console.write("no glob file %s " % glob_cov_file + '\n')
            return
        open_coverage(glob_cov_file)

    @classmethod
    def runtestnocov_action(cls):
        GSHTestsuite(
            "python %s/testsuite -j0 -o %s/out -t %s/tmp" %
            (TS_DIR, TS_DIR, TS_DIR))

    @classmethod
    def build_action(cls):
        GSHCommand("make", exit_fun=GSHActions.install_action)

    @classmethod
    def install_action(cls):
        GSHCommand("make install")

    @classmethod
    def console_action(cls):
        Console_Process("obj/dev/gsh_unit")


class TestsuiteWidget(object):

    def create_widget(self):
        self.box = Gtk.VBox()
        self.scroll = Gtk.ScrolledWindow()
        self.store = Gtk.TreeStore(str, str, str, str, int, int, str)
        self.view = Gtk.TreeView(self.store)
        self.view.set_rules_hint(True)
        self.scroll.add(self.view)
        self.box.pack_start(self.scroll, True, True, 0)

        # Add columns
        col = Gtk.TreeViewColumn("Name", Gtk.CellRendererText(), text=3)
        self.view.append_column(col)
        col = Gtk.TreeViewColumn("Status", Gtk.CellRendererText(), text=1,
                                 background=2)
        self.view.append_column(col)
        col = Gtk.TreeViewColumn("Description",
                                 Gtk.CellRendererText(), text=0)
        col.set_expand(True)
        self.view.append_column(col)
        self.view.connect("button_press_event", self.on_click)

    def on_click(self, view, event):
        if event.button == 1:
            results = self.view.get_path_at_pos(event.x, event.y)
            if results:
                path, _, _, _ = results
                if self.store[path][6]:
                    # We have a row in our tree. If the associate cov exist
                    # generate an xml file and open it
                    gcov_file = self.store[path][6][:-5] + '.cov.json'
                    if not os.path.isfile(gcov_file):
                        return
                    open_coverage(gcov_file)

    def find_all_results(self):
        pass

    def add_result(self, test_name):
        import yaml
        test_yaml = os.path.join(TS_DIR,
                                 'out', 'new', test_name + ".yaml")
        if not os.path.isfile(test_yaml):
            return

        # Load test result
        with open(test_yaml, 'rb') as fd:
            content = fd.read()
            # Discard python types that may not be available in gps
            content = re.sub(r'!![^ \n\r]*\n*', r'', content, re.S)
            content = yaml.load(content)

        # First update parents node
        test_case_dir = os.path.dirname(content['test_env']['test_case_file'])
        test_case_els = test_case_dir.replace('\\', '').split('/')
        for index in range(1, len(test_case_els)):
            tmp = "/".join(test_case_els[0:index])
            tmp_paren = "/".join(test_case_els[0:index - 1])
            if not tmp_paren:
                tmp_paren = None
            if tmp not in self.store_nodes:
                if tmp_paren is None:
                    p = None
                else:
                    p = self.store_nodes[tmp_paren]
                self.store_nodes[tmp] = self.store.append(p)
                self.store[self.store_nodes[tmp]] = ['',
                                                     '',
                                                     TEST_COLOR['PASSED'],
                                                     test_case_els[index - 1],
                                                     0, 0, '']

            n = self.store_nodes[tmp]
            self.store[n][5] += 1
            if content['status'] in ('FAILED', 'PROBLEM'):
                self.store[n][4] += 1
                self.store[n][2] = TEST_COLOR['FAILED']
            self.store[n][1] = "%s/%s" % (self.store[n][4], self.store[n][5])

        n = self.store.append(self.store_nodes[tmp])
        self.store[n] = [content['test_env']['title'],
                         content['status'],
                         TEST_COLOR.get(content['status'], ''),
                         os.path.basename(test_case_dir), 0, 0,
                         test_yaml]
        self.add_to_store(content, n, TEST_COLOR.get(content['status'], ''))

        GPS.MDI.add(self.box, title="Testsuite")

    def __init__(self):
        self.create_widget()

        self.store_nodes = {}

    def add_to_store(self, obj, parent, color):
        for k in obj:
            data = self.store.append(parent)
            if isinstance(obj[k], dict):
                self.add_to_store(obj[k], data, color)
                self.store[data] = ['',
                                    '',
                                    color,
                                    k, 0, 0, '']
            else:
                self.store[data] = [str(obj[k]), '', color, k, 0, 0, '']


def initialize_project_plugin():
    GSHActions()


def finalize_project_plugin():
    pass
