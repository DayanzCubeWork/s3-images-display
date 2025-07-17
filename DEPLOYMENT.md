# Deploying to Render

This guide will help you deploy your S3 Image Dashboard to Render.

## Prerequisites

1. A Render account (free tier available)
2. Your code pushed to a Git repository (GitHub, GitLab, etc.)
3. AWS S3 credentials and bucket name

## Step 1: Prepare Your Repository

Make sure your repository contains these files:
- `app.py` - Your Flask application
- `requirements.txt` - Python dependencies
- `render.yaml` - Render configuration
- `gunicorn.conf.py` - Gunicorn configuration
- `templates/` - HTML templates

## Step 2: Deploy to Render

### Option A: Using render.yaml (Recommended)

1. Push your code to a Git repository
2. Go to [Render Dashboard](https://dashboard.render.com/)
3. Click "New +" and select "Blueprint"
4. Connect your Git repository
5. Render will automatically detect the `render.yaml` file
6. Click "Apply" to deploy

### Option B: Manual Deployment

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click "New +" and select "Web Service"
3. Connect your Git repository
4. Configure the service:
   - **Name**: `s3-image-dashboard` (or your preferred name)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: Free (or paid if needed)

## Step 3: Configure Environment Variables

In your Render service dashboard, go to "Environment" and add these variables:

- `S3_BUCKET_NAME` - Your S3 bucket name
- `AWS_ACCESS_KEY_ID` - Your AWS access key
- `AWS_SECRET_ACCESS_KEY` - Your AWS secret key
- `AWS_REGION` - Your AWS region (e.g., `us-west-1`)

## Step 4: Deploy

1. Click "Create Web Service"
2. Render will build and deploy your application
3. Once deployed, you'll get a URL like `https://your-app-name.onrender.com`

## Important Notes

- **Free Tier Limitations**: Free tier services sleep after 15 minutes of inactivity
- **Environment Variables**: Never commit sensitive credentials to your repository
- **S3 Permissions**: Ensure your AWS credentials have read access to your S3 bucket
- **CORS**: If you need to access this from other domains, you may need to configure CORS

## Troubleshooting

### Common Issues

1. **Build Failures**: Check that all dependencies are in `requirements.txt`
2. **Environment Variables**: Ensure all required env vars are set in Render
3. **S3 Access**: Verify your AWS credentials have proper permissions
4. **Port Issues**: Render automatically sets the PORT environment variable

### Logs

Check the logs in your Render dashboard to debug any issues:
1. Go to your service dashboard
2. Click on "Logs" tab
3. Look for error messages during build or runtime

## Security Considerations

- Use IAM roles with minimal required permissions
- Consider using AWS Secrets Manager for production
- Enable HTTPS (automatic on Render)
- Regularly rotate your AWS credentials 