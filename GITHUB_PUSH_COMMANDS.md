# GitHub Push Commands

## After creating your GitHub repository, run these commands:

```bash
# Add the remote repository (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/dam-compliance-analyzer.git

# Push to GitHub
git branch -M main
git push -u origin main
```

## Verify the push worked:
```bash
git remote -v
```

## If you need to change the remote URL later:
```bash
git remote set-url origin https://github.com/YOUR_USERNAME/your-repo-name.git
```

## Example with a real username:
If your GitHub username is "johndoe", the commands would be:
```bash
git remote add origin https://github.com/johndoe/dam-compliance-analyzer.git
git branch -M main
git push -u origin main
```