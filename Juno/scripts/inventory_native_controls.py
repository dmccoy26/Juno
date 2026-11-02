"""Inventory native interaction declarations; discovery is not a passing interaction test."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
rows=[]
pattern=re.compile(r'\b(Button|Toggle|Picker|TextField|SecureField|DatePicker|DisclosureGroup|TextEditor|List)\s*(?:\([^\n]*?)?(?=\{|$)|\.(alert|sheet|contextMenu|onSubmit)\b')
for file in sorted((ROOT/'desktop').glob('*.swift')):
    for number,line in enumerate(file.read_text().splitlines(),1):
        for match in pattern.finditer(line):
            rows.append({'file':str(file.relative_to(ROOT)),'line':number,'kind':match.group(1) or match.group(2),'declaration':line.strip(),'status':'inventoried; interaction evidence required'})
output=ROOT/'docs/reports/native-controls-2026-11-01.json'
output.write_text(json.dumps({'notice':'Declaration inventory, not evidence every state or action passed. Native, isolated API and external-account coverage are recorded separately.','controls':rows},indent=2)+'\n')
print(f'Inventoried {len(rows)} control declarations. '+str(output))
