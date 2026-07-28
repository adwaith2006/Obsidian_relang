package main

import (
	"fmt"
	"rsc.io/qr"
)

func main() {
	code, err := qr.Encode("https://example.com", qr.L)
	if err != nil {
		panic(err)
	}
	fmt.Printf("Go rsc.io/qr Size: %d\n", code.Size)
	for i := 0; i < code.Size; i++ {
		for j := 0; j < code.Size; j++ {
			if code.Black(j, i) {
				fmt.Print("1")
			} else {
				fmt.Print("0")
			}
		}
		fmt.Println()
	}
}
