import re

class Jid:
    name = None
    server = None
    resource = None

    def __init__(self, jid):
        r = re.compile(r"([^@]+)@([^/]+)(?:/(.+))?")
        m = re.match(r, jid)
        self.name = m.group(1)
        self.server = m.group(2)
        self.resource = m.group(3)


    @property
    def bare(self):
        return "%s@%s" % (self.name, self.server)

    def __str__(self):
        return "%s@%s%s" % (self.name, self.server, "/%s" % self.resource if self.resource is not None else "")

def jid2wa(jid):
    jid = Jid(jid)
    return "%s@s.whatsapp.org" % jid.name
