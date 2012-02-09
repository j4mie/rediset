rm -r ./docs/build
cd docs
d
rsync --exclude='*.git' --delete -a ./build/ ../gh-pages/
cd ../gh-pages/
touch .nojekyll
git add .
git commit -m 'Update docs'
git push origin gh-pages
