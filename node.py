class Node:
    async def client_request(self, request, signature):
        pass
    async def pre_prepare(self, view, sequence, request, signature):
        pass
    async def prepare(self, view, sequence, request, signature):
        pass
    async def commit(self, view, sequence, request, signature):
        pass
    async def view_change(self, new_view, prepared_certs, signature):
        pass
    async def new_view(self, new_view, omicron, theta, signature):
        pass
    def get_pk(self):
        pass
    def is_primary(self):
        return False
