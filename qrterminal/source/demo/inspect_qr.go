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
	fmt.Printf("Size: %d, Scale: %d\n", code.Size, code.Scale)
	fmt.Println("Matrix:")
	for y := 0; y < code.Size; y++ {
		for x := 0; x < code.Size; x++ {
			if code.Black(x, y) {
				fmt.Print("1")
			} else {
				fmt.Print("0")
			}
		}
		fmt.Println()
	}
}
