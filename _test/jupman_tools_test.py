from hypothesis import given
from pprint import pprint
from hypothesis.strategies import text
import sys
sys.path.append('../')
sys.path.append('.')  # good lord, without this debugging in VSCode doesn't work
import jupman_tools as jmt
from jupman_tools import ignore_spaces, tag_regex, Jupman
import pytest 
import re
from sphinx.application import Sphinx
import os
import nbformat

from common_test import * 
import datetime

def test_detect_release():
    res =  jmt.detect_release()
    assert res == 'dev' or len(res.split('.')) >= 2

def test_get_version():
    res =  jmt.get_version(jmt.detect_release())
    assert res == 'dev' or len(res.split('.')) == 2


def test_parse_date():
    assert jmt.parse_date('2000-12-31') == datetime.datetime(2000,12,31)

    with pytest.raises(Exception):
        jmt.parse_date('2000-31-12')

def test_parse_date_str():
    assert jmt.parse_date_str('2000-12-31') == '2000-12-31'
    
    with pytest.raises(Exception):
        jmt.parse_date_str('2000-31-12')


def test_jupman_constructor():
    jm = Jupman()
    # only testing the vital attrs
    assert jm.filename == 'jupman'
    #NOTE: putting '/' at the end causes exclude_patterns to not work !
    assert jm.build == '_build' 
    assert jm.generated == '_static/generated'

class MockSphinx:
    def add_config_value(self, a,b,c):
        pass
    def add_transform(self, a):
        pass
    def add_javascript(self, a):
        pass
    def add_stylesheet(self, a):
        pass


def test_uproot():
    assert jmt.uproot('jupman.py') == ''
    assert jmt.uproot('_test/') == '../'
    assert jmt.uproot('_test/test-chapter/data/pop.csv') == '../../../'
    # this is supposed to be a directory
    assert jmt.uproot('_test/non-existing') == '../../'
    assert jmt.uproot('_static/img') == '../../'
    assert jmt.uproot('_static/img/cc-by.png') == '../../'
    assert jmt.uproot('_static/img/non-existing') == '../../../'

def test_replace_sysrel():

    assert jmt.replace_py_rel("""import sys
sys.do_something()""", 'python-example').strip() ==  """import sys
sys.do_something()"""


    assert jmt.replace_py_rel("""
import sys
sys.path.append('../')
import jupman

    """, 'python-example').strip() ==  'import jupman'


    assert jmt.replace_py_rel("""
import sys
sys.path.append('../')
import jupman
sys.do_something()
    """, 'python-example').strip() ==  """import sys
import jupman
sys.do_something()"""


def test_is_zip_ignored():
    jm = make_jm()
    assert jm.is_zip_ignored('.ipynb_checkpoints')
    assert jm.is_zip_ignored('prova/.ipynb_checkpoints')
    assert jm.is_zip_ignored('prova/__pycache__')
    assert not jm.is_zip_ignored('good')
    assert not jm.is_zip_ignored('very/good')
    

def test_is_code_sol_to_strip():
    jm = make_jm()
    solution = '# SOLUTION\nx=5\n'
    write_here = '# write here\nx=5\n'
    jupman_raise = '#jupman-raise\nx=5\n#/jupman-raise\n'
    jupman_strip = '#jupman-strip\nx=5\n#/jupman-strip\n'
    jupman_purge = '#jupman-purge\nx=5\n#/jupman-purge\n'

    assert jm.is_to_strip(solution) == True
    assert jm.is_to_strip(write_here) == True
    assert jm.is_to_strip(jupman_raise) == True
    assert jm.is_to_strip(jupman_strip) == True
    assert jm.is_to_strip(jupman_purge) == True

    assert jm.is_code_sol(solution) == True
    assert jm.is_code_sol(write_here) == True    
    assert jm.is_code_sol(jupman_raise) == True
    assert jm.is_code_sol(jupman_strip) == True
    assert jm.is_code_sol(jupman_purge) == False
    
    cx = """x = 9
#jupman-purge
# present neither in solution nor in exercises
# NOTE: this is NOT considered a solution
y = 'purged!'
#/jupman-purge
# after"""
    assert jm.is_to_strip(cx) == True
    assert jm.is_code_sol(cx) == False

def test_copy_chapter():
    clean()
    
    jm = make_jm()
    os.makedirs(jm.build)
    dest_dir = os.path.join(jm.build, 'test-chapter')
    jm.copy_code('_test/test-chapter',
                 dest_dir,
                 copy_solutions=True)

    assert os.path.isdir(dest_dir)

    replacements_fn = os.path.join(dest_dir, 'replacements.ipynb')
    assert os.path.isfile(replacements_fn)

    nb_node = nbformat.read(replacements_fn, nbformat.NO_CONVERT)

    # markdown                             
    assert '[some link](index.ipynb)' in nb_node.cells[1].source
    assert '![some link](_static/img/cc-by.png)' in nb_node.cells[2].source
    assert '[some link](data/pop.csv)' in nb_node.cells[3].source

    assert '<a href="index.ipynb" target="_blank">a link</a>' in nb_node.cells[4].source
    
    assert '<img src="_static/img/cc-by.png">' in nb_node.cells[5].source
    assert '<a href="data/pop.csv">a link</a>' in nb_node.cells[6].source
    
    assert '<a href="index.ipynb">a link</a>' in nb_node.cells[7].source

    assert '<img src="_static/img/cc-by.png">' in nb_node.cells[8].source

    assert '<a href="data/pop.csv">a link</a>' in nb_node.cells[9].source

    assert '# Python\nimport jupman' in nb_node.cells[10].source
    assert '#jupman-raise' in nb_node.cells[10].source

    assert '<a href="index.html">a link</a>' in nb_node.cells[11].source
    
    assert '<a href="https://jupman.softpython.org">a link</a>' in nb_node.cells[12].source

    py_fn = os.path.join(dest_dir, 'file.py')
    assert os.path.isfile(py_fn)

    with open(py_fn, encoding='utf-8') as py_f:
        py_code = py_f.read()
        assert '# Python\nimport jupman' in py_code
        assert '#jupman-raise' in py_code

    test_fn = os.path.join(dest_dir, 'some_test.py')
    assert os.path.isfile(test_fn)

    with open(test_fn, encoding='utf-8') as test_f:
        test_code = test_f.read()
        assert 'some_sol' not in test_code
        assert '# Python\nimport some\nimport jupman' in test_code
        assert '#jupman-raise' in test_code

    sol_fn = os.path.join(dest_dir, 'some_sol.py')
    assert os.path.isfile(sol_fn)

    with open(sol_fn, encoding='utf-8') as py_sol_f:
        sol_code = py_sol_f.read()
        assert '# Python\nimport jupman' in sol_code
        assert '#jupman-raise' not in sol_code
        assert '#jupman-strip' not in sol_code
        assert '#jupman-purge' not in sol_code
        assert 'stripped!' in sol_code
        assert 'purged!' not in sol_code        
        assert "# work!\n\nprint('hi')" in sol_code

    ex_fn = os.path.join(dest_dir, 'some.py')
    assert os.path.isfile(ex_fn)

    with open(ex_fn, encoding='utf-8') as py_ex_f:
        py_ex_code = py_ex_f.read()
        assert '# Python\nimport jupman' in py_ex_code
        assert '#jupman-raise' not in py_ex_code
        assert '# work!\nraise' in py_ex_code

    # nb_ex ----------------------------
    nb_ex_fn = os.path.join(dest_dir, 'nb.ipynb')
    assert os.path.isfile(nb_ex_fn)

    nb_ex = nbformat.read(nb_ex_fn, nbformat.NO_CONVERT)
    
    #pprint(nb_ex)
    assert "# Notebook EXERCISES" in nb_ex.cells[0].source
    assert "#before\nraise" in nb_ex.cells[1].source
    assert nb_ex.cells[2].source == ""   # SOLUTION strips everything
    assert nb_ex.cells[3].source.strip() == "# 3\n# write here"    # write here strips afterwards
    #4 question
    #5 answer: must begin with answer and strips everything after
    assert nb_ex.cells[5].source == '**ANSWER**:\n'
    #6 write here 
    assert nb_ex.cells[6].source == 'x = 6\n# write here fast please\n\n'
    assert nb_ex.cells[7].source == '' # SOLUTION strips everything
    assert nb_ex.cells[8].source == 'x = 8\n\n# after'  # jupman-strip  strips everything inside exercises
    assert nb_ex.cells[9].source == 'x = 9\n\n# after'  # jupman-purge everything inside exercises 
    assert '#jupman-strip' not in nb_ex.cells[10].source   
    assert '#jupman-purge' not in nb_ex.cells[10].source   

    # nb_sol --------------------
    nb_sol_fn = os.path.join(dest_dir, 'nb-sol.ipynb')
    nb_sol = nbformat.read(nb_sol_fn, nbformat.NO_CONVERT) 
    assert 'stripped!' in nb_sol.cells[8].source   # jupman-strip  strips everything inside exercises
    assert '#jupman-strip' not in nb_sol.cells[8].source   
    assert 'purged!' not in  nb_sol.cells[9].source  # jupman-purge  strips everything also in solutions    
    assert '#jupman-purge' not in nb_sol.cells[9].source           
    
    assert '#jupman-strip' not in nb_sol.cells[10].source   
    assert '#jupman-purge' not in nb_sol.cells[10].source       
    assert 'stripped!' in nb_sol.cells[10].source
    assert not 'purged!' in nb_sol.cells[10].source

    # nb_sol_web --------------------
    nb_sol_fn = os.path.join(dest_dir, 'nb-sol.ipynb')
    nb_sol_web = nbformat.read(nb_sol_fn, nbformat.NO_CONVERT)

    jm._sol_nb_to_ex(nb_sol_web,
                     os.path.abspath(nb_sol_fn),
                     website=True)
    
    stripped8 = 0
    stripped10 = 0
    for cell in nb_sol_web.cells:
        if 'stripped!8' in cell.source:
            stripped8 += 1
        if 'stripped!10' in cell.source:
            stripped10 += 1    
        assert not 'purged!9' in cell.source
        assert not 'purged!10' in cell.source
    assert stripped8 == 1
    assert stripped10 == 1

    # chal --------------------
    py_chal_sol_fn = os.path.join(dest_dir, 'my_chal_sol.py')    
    assert not os.path.isfile(py_chal_sol_fn)
    py_chal_fn = os.path.join(dest_dir, 'my_chal.py')
    assert os.path.isfile(py_chal_fn)

    py_chal_test_fn = os.path.join(dest_dir, 'my_chal_test.py')
    assert os.path.isfile(py_chal_test_fn)
    with open(py_chal_test_fn) as py_chal_test_f: 
        py_chal_test_code = py_chal_test_f.read()
        assert 'from my_chal import *' in py_chal_test_code

    nb_chal_ex_fn = os.path.join(dest_dir, 'nb-chal.ipynb')    
    assert os.path.isfile(nb_chal_ex_fn)
    nb_chal_sol_fn = os.path.join(dest_dir, 'nb-chal-sol.ipynb')
    assert not os.path.isfile(nb_chal_sol_fn)

    nb_chal_ex = nbformat.read(nb_chal_ex_fn, nbformat.NO_CONVERT)

    assert jm.ipynb_solutions not in nb_chal_ex.cells[1].source
    


def test_setup(tconf):
        
    mockapp = MockSphinx()
    
    tconf.setup(mockapp)
    # if so tests run smoothly also on non-jupman projects
    if os.path.exists('jupyter-example'):
        assert os.path.isfile(os.path.join(tconf.jm.generated, 'jupyter-example.zip'))
    if os.path.exists('python-example'):
        assert os.path.isfile(os.path.join(tconf.jm.generated, 'python-example.zip'))
    if os.path.exists('jup-and-py-example'):
        assert os.path.isfile(os.path.join(tconf.jm.generated, 'jup-and-py-example.zip'))
    if os.path.exists('challenge-example'):
        assert os.path.isfile(os.path.join(tconf.jm.generated, 'challenge-example.zip'))

def test_tag_regex():
    
    with pytest.raises(ValueError):
        tag_regex("")

    p = re.compile(tag_regex(" a    b"))
    assert p.match(" a b")
    assert p.match(" a  b")
    assert p.match(" a  b ")
    assert p.match(" a  b  ")
    assert p.match(" a  b\n")
    assert p.match("   a  b\n")
    assert not p.match(" ab")
    assert not p.match("c b")

def test_write_solution_here():
    jm = make_jm()
    p = re.compile(jm.write_solution_here)
    #print(p)
    assert p.match(" # write here a b\nc")
    assert p.match(" # write here a   b c \nc\n1d")    
    assert p.match('#  write  here\n')
    #assert p.match('# write here')  # corner case, there is no \n    
    #assert p.match('# write here   ')  # corner case, there is no \n    

def test_validate_code_tags():
    jm = make_jm()
    assert jm.validate_code_tags('# SOLUTION\nbla', 'some_file') == 1
    assert jm.validate_code_tags('  # SOLUTION\nbla', 'some_file') == 1
    assert jm.validate_code_tags('something before  # SOLUTION\nbla', 'some_file') == 0
    assert jm.validate_code_tags('#jupman-strip\nblabla#/jupman-strip', 'some_file') == 1
    assert jm.validate_code_tags('#jupman-purge\nblabla#/jupman-purge', 'some_file') == 1
    # pairs count as one
    assert jm.validate_code_tags('#jupman-raise\nsomething#/jupman-raise', 'some_file') == 1
    assert jm.validate_code_tags("""
    hello
    #jupman-raise
    something
    #/jupman-raise
    #jupman-raise
    bla
    #/jupman-raise""", 'some_file') == 2

def test_validate_markdown_tags():
    jm = make_jm()

    assert jm.validate_markdown_tags('**ANSWER**: hello', 'some_file') == 1
    assert jm.validate_markdown_tags('  **ANSWER**: hello', 'some_file') == 1
    assert jm.validate_markdown_tags('bla  **ANSWER**: hello', 'some_file') == 0