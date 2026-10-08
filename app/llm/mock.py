import re
from app.schemas import ExtractedRequest, Item, Contact
class MockProvider:
    def extract(self, message, now):
        t=message.lower()
        garments={"shirt":r"shirts?","pants":r"pants|trousers|jeans","jacket":r"jackets?|blazer","dress":r"dress(?:es)?","skirt":r"skirts?","coat":r"coats?"}
        matches=sorted((m.start(),g) for g,p in garments.items() for m in re.finditer(r"\b(?:"+p+r")\b",t))
        alterations={"hem":r"hem|shorten.*(?:pants|dress|skirt)","take_in":r"take in|taken in|tighten","let_out":r"let out|loosen","sleeve_length":r"sleeve","zipper":r"zipper","button":r"button","patch":r"patch","repair":r"repair|fix|mend"}
        items=[]
        for index,(start,g) in enumerate(matches):
            left=0 if index==0 else start
            right=matches[index+1][0] if index+1<len(matches) else len(t)
            chunk=t[left:right]
            types=[a for a,p in alterations.items() if re.search(p,chunk)]
            if not types: types=[a for a,p in alterations.items() if re.search(p,t)] if len(matches)==1 else []
            flags=[f for f in ["leather","silk","beaded","lined","formal","stretch"] if f in chunk]
            if "wedding" in chunk and "formal" not in flags:flags.append("formal")
            items.append(Item(garment=g,alteration_types=types,material_flags=flags or ["unknown"]))
        email=re.search(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}",message)
        phone=re.search(r"(?<!\d)(?:\+1[ -]?)?(?:\(\d{3}\)|\d{3})[ -]?\d{3}[ -]?\d{4}(?!\d)",message)
        name=re.search(r"(?:my name is|I'm|I am) ([A-Z][a-z]+(?: [A-Z][a-z]+)?)",message)
        event=next((e for e in ["wedding","interview","prom","graduation","funeral"] if re.search(r"\b"+e+r"\b",t)),"none")
        owned=False if re.search(r"not (?:bought|purchased)|haven't bought|haven’t bought|buying|don't own|do not own",t) else True if re.search(r"i have|i own|my pants|my jacket|my dress",t) else "unknown"
        return ExtractedRequest(items=items,event=event,customer_has_garment=owned,contact=Contact(name=name.group(1) if name else None,email=email.group() if email else None,phone=phone.group() if phone else None),is_in_scope=not bool(re.search(r"dry[ -]?clean|lost my|damaged my|opening hours|where are you",t)),notes="Deterministic mock extraction; human review required.").model_dump(mode="json")
