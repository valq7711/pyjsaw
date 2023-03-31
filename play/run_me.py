from pathlib import Path
from pyjsaw.compiler import compile


#mod_fp = (Path(__file__).parent / 'vue_example.py')
mod_fp = (Path(__file__).parent / 'vue_example_class_style.py')
out = compile(mod_fp)

print(out)
out_fp = (Path(__file__).parent / 'out_tst.js')
out_fp.write_text(out, encoding='utf8')
