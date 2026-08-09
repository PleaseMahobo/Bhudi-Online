package main

import (
	"image"
	_ "image/jpeg"
	_ "image/png"
	"os"
)

func loadImageFile(path string) (image.Image, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	img, _, err := image.Decode(f)
	return img, err
}
