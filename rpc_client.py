# import json, socket

# s = socket.create_connection(("localhost", 1234))
# s.sendall(
#     json.dumps({"id": 1, "method": "RPCFunc.Echo", "params": ["Cupid's Arrow"]}).encode())
# print((s.recv(4096)).decode())

# Sample functions, for use with RPCServer.go

from jsonclient import JSONClient

rpc = JSONClient(("localhost", 1234))

for i in range(10):
    print(rpc.call("RPCFunc.Add", i))

for i in range(10):
    print(rpc.call("RPCFunc.DictLen", {str(i):i+1}))

for i in range(10):
    print(rpc.call("RPCFunc.Echo", str(i)))

