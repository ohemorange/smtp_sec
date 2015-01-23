// RPC from http://www.artima.com/weblogs/viewpost.jsp?thread=333589

// Sample calls, for use with rpc_client.py

package main

import (
  "net/rpc/jsonrpc"
  "net/rpc"
  "net"
  "log"
  "strconv"
)

type RPCFunc struct {} // Callable by JSON-RPC

// must have key type string
func (*RPCFunc) DictLen(arg *map[string]int, result *int) error {
  for k, v := range *arg {
    log.Print("Arg passed: "+string(k)+" "+strconv.Itoa(v))
  }
  *result = len(*arg)
  return nil
}

func (*RPCFunc) Add(arg *int, result *int) error {
  log.Print("Arg passed: " + strconv.Itoa(*arg))
  *result = *arg + 1
  return nil
}

func (*RPCFunc) Echo(arg *string, result *string) error {
  log.Print("Arg passed: " + *arg)
  *result = ">" + *arg + "<"
  return nil
}

func main() {
  log.Print("Starting Server...")
  l, err := net.Listen("tcp", "localhost:1234")
  if err != nil {
    log.Fatal(err)
  }
  defer l.Close()
  log.Print("listening on: ", l.Addr())
  rpc.Register(new (RPCFunc))
  for {
    log.Print("waiting for connections...")
    conn, err := l.Accept()
    if err != nil {
      log.Printf("accept error: %s", conn)
      continue
    }
    log.Printf("connection started: %v", conn.RemoteAddr())
    go jsonrpc.ServeConn(conn)
  }
}