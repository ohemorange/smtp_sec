# import json, socket
#
# s = socket.create_connection(("localhost", 1234))
# s.sendall(
#     json.dumps({"id": 1, "method": "RPCFunc.Echo", "params": ["Cupid's Arrow"]}).encode())
# print((s.recv(4096)).decode())


from jsonclient import JSONClient

rpc = JSONClient(("localhost", 1234))

for i in range(100):
    print(rpc.call("RPCFunc.Echo", "hello " + str(i)))