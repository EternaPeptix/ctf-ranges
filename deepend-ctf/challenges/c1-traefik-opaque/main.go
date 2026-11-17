// c1 / CVE-2026-88009 — Traefik URL.Opaque routing-vs-forwarding desync.
//
// Go's net/url stores a "rootless" request target (e.g. `http:admin/flag`) in
// URL.Opaque, leaving URL.Path empty. The edge evaluates its ACL on URL.Path
// (so it sees "/", allowed), but forwards URL.Opaque verbatim to the backend —
// so the backend serves the admin route the ACL thought it had blocked.
//
// Isolated training range — do not deploy.
package main

import (
	"io"
	"log"
	"net/http"
	"strings"
)

const FLAG = "0DAY{traefik_url_0paque_r0ut1ng_d3sync}"

// internal backend (loopback only)
func backend() {
	mux := http.NewServeMux()
	mux.HandleFunc("/admin/flag", func(w http.ResponseWriter, r *http.Request) {
		io.WriteString(w, "admin control panel\n"+FLAG+"\n")
	})
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		io.WriteString(w, "public site: nothing to see here\n")
	})
	log.Fatal(http.ListenAndServe("127.0.0.1:9000", mux))
}

func edge(w http.ResponseWriter, r *http.Request) {
	path := r.URL.Path // ACL / routing are evaluated on the parsed Path

	if strings.HasPrefix(path, "/admin") {
		w.WriteHeader(http.StatusForbidden)
		io.WriteString(w, "403 blocked by edge ACL (/admin is internal-only)\n")
		return
	}

	// BUG: forward URL.Opaque verbatim when present, instead of the vetted Path
	fwd := path
	if fwd == "" {
		fwd = "/"
	}
	if r.URL.Opaque != "" {
		fwd = "/" + r.URL.Opaque
	}

	req, err := http.NewRequest(r.Method, "http://127.0.0.1:9000"+fwd, nil)
	if err != nil {
		w.WriteHeader(http.StatusBadGateway)
		return
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		w.WriteHeader(http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}

func main() {
	go backend()
	log.Println("[c1] edge on :80 -> backend 127.0.0.1:9000")
	log.Fatal(http.ListenAndServe(":80", http.HandlerFunc(edge)))
}
