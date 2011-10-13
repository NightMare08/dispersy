from time import time

from dispersydatabase import DispersyDatabase
from member import Member

if __debug__:
    from dprint import dprint

    def is_address(address):
        assert isinstance(address, tuple), type(address)
        assert len(address) == 2, len(address)
        assert isinstance(address[0], str), type(address[0])
        assert address[0], address[0]
        assert isinstance(address[1], int), type(address[1])
        assert address[1] >= 0, address[1]
        return True

class Candidate(object):
    """
    A wrapper around the candidate table in the dispersy database.
    """
    def __init__(self, address, lan_address, wan_address, community=None, is_walk=False, is_stumble=False, is_introduction=False):
        if __debug__:
            from community import Community
        assert is_address(address)    
        assert is_address(lan_address)
        assert is_address(wan_address)
        assert address == lan_address or address == wan_address
        assert isinstance(is_walk, bool)
        assert isinstance(is_stumble, bool)
        assert community is None or isinstance(community, Community)
        if __debug__: dprint("discovered ", wan_address[0], ":", wan_address[1], " (", lan_address[0], ":", lan_address[1], ")")
        self._address = address
        self._lan_address = lan_address
        self._wan_address = wan_address
        self._is_walk = is_walk
        self._is_stumble = is_stumble
        self._is_introduction = is_introduction
        self._timestamp_incoming = time()
        self._timestamp_last_step = {community.cid:time() - 30.0} if community else {}

    @property
    def address(self):
        return self._address
        
    @property
    def lan_address(self):
        return self._lan_address

    @property
    def wan_address(self):
        return self._wan_address

    @property
    def is_walk(self):
        return self._is_walk

    @property
    def is_stumble(self):
        return self._is_stumble

    @property
    def is_introduction(self):
        return self._is_introduction
    
    @property
    def timestamp_incoming(self):
        return self._timestamp_incoming

    def timestamp_last_step_in_community(self, community, default=0.0):
        return self._timestamp_last_step.get(community.cid, default)
    
    def in_community(self, community):
        return community.cid in self._timestamp_last_step

    def timeout(self, community):
        """
        Called on timeout of a dispersy-introduction-response message

        Returns True if there are communities left where this candidate did not timeout.
        """
        try:
            self._timestamp_last_step.pop(community.cid)
        except KeyError:
            pass
        return bool(self._timestamp_last_step)

    def get_timestamp_incoming(self, community, default=0.0):
        return self._timestamp_last_step.get(community.cid, default)
    
    def out_introduction_request(self, community):
        self._timestamp_last_step[community.cid] = time()
        
    def inc_introduction_requests(self, lan_address, wan_address):
        assert is_address(lan_address)
        assert is_address(wan_address)
        if __debug__: dprint("updated ", wan_address[0], ":", wan_address[1], " (", lan_address[0], ":", lan_address[1], ")")
        self._lan_address = lan_address
        self._wan_address = wan_address
        self._is_stumble = True

    def inc_introduction_response(self, lan_address, wan_address):
        assert is_address(lan_address)
        assert is_address(wan_address)
        if __debug__: dprint("updated ", wan_address[0], ":", wan_address[1], " (", lan_address[0], ":", lan_address[1], ")")
        self._lan_address = lan_address
        self._wan_address = wan_address
        self._is_walk = True

    def inc_introduced(self):
        if __debug__: dprint("updated")
        self._is_introduction = True

    def inc_puncture(self, address, lan_address, wan_address):
        assert is_address(address)
        assert is_address(lan_address)
        assert is_address(wan_address)
        assert address == lan_address or address == wan_address
        if __debug__: dprint("updated ", wan_address[0], ":", wan_address[1], " (", lan_address[0], ":", lan_address[1], ")")
        self._address = address
        self._lan_address = lan_address
        self._wan_address = wan_address

    def inc_any(self, community):
        if __debug__:
            from community import Community
        assert isinstance(community, Community)
        if __debug__: dprint("updated ", self._wan_address[0], ":", self._wan_address[1], " (", self._lan_address[0], ":", self._lan_address[1], ")")
        if not community.cid in self._timestamp_last_step:
            self._timestamp_last_step[community.cid] = time() - 30.0
        self._timestamp_incoming = time()

    @property
    def members(self):
        # TODO we should not just trust this information, a member can put any address in their
        # dispersy-identity message.  The database should contain a column with a 'verified' flag.
        # This flag is only set when a handshake was successful.
        host, port = self._address
        return [Member.get_instance(str(public_key))
                for public_key,
                in list(DispersyDatabase.get_instance().execute(u"SELECT DISTINCT member.public_key FROM identity JOIN member ON member.id = identity.member WHERE identity.host = ? AND identity.port = ? -- AND verified = 1", (unicode(host), port)))]

class BootstrapCandidate(Candidate):
    def __init__(self, wan_address):
        super(BootstrapCandidate, self).__init__(wan_address, wan_address, wan_address)
