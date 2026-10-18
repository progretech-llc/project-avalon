// Only the native encrypted Harness socket is reachable through discovery.
package main

import (
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"time"
)

func main() {
	target, _ := url.Parse("http://127.0.0.1:18895")
	proxy := httputil.NewSingleHostReverseProxy(target)
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/harness/ws" || r.Method != http.MethodGet || r.URL.RawQuery != "" || r.Header.Get("Origin") != "" {
			http.NotFound(w, r)
			return
		}
		proxy.ServeHTTP(w, r)
	})
	server := &http.Server{Addr: ":18894", Handler: handler, ReadHeaderTimeout: 5 * time.Second, MaxHeaderBytes: 16384}
	log.Fatal(server.ListenAndServe())
}
