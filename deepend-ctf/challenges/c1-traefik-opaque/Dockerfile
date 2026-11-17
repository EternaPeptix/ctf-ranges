FROM golang:1.23-alpine
WORKDIR /app
COPY main.go .
RUN go mod init deepend-c1 >/dev/null 2>&1 && go build -o server main.go
EXPOSE 80
CMD ["./server"]
