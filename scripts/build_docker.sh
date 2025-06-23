#!/bin/bash

# Docker Build and Push Script for Single Dockerfile Project
# Usage: ./build-docker.sh [options] [tag]
# Options: -p/--push to push to GHCR, -h/--help for usage

set -euo pipefail  # Exit on error, undefined vars, and pipe failures

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Default values
TAG="1.0"
PUSH_IMAGE=false
REGISTRY="ghcr.io"
REPO_NAME=$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")
GITHUB_USERNAME="fonality-code"
APP_NAME="app"  # Generic name for the single app

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--push)
            PUSH_IMAGE=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            if [[ "$TAG" == "1.0" ]]; then
                TAG="$1"
            fi
            shift
            ;;
    esac
done

# Function to show usage
show_usage() {
    echo "Usage: $0 [options] [tag]"
    echo ""
    echo "Options:"
    echo "  -p, --push    Push the image to GHCR after building"
    echo "  -h, --help    Show this help message"
    echo ""
    echo "Parameters:"
    echo "  tag       - Docker tag to use (default: '1.0')"
    echo ""
    echo "Examples:"
    echo "  $0                    # Build with '1.0' tag"
    echo "  $0 dev                # Build with 'dev' tag"
    echo "  $0 -p prod            # Build and push with 'prod' tag"
    echo "  $0 --push             # Build and push with '1.0' tag"
    echo ""
}

# Function to prompt user for tag confirmation/change
prompt_tag_change() {
    print_status "Current tag: $TAG"
    read -p "Do you want to change the tag? (y/N): " change_tag

    if [[ "$change_tag" =~ ^[Yy]$ ]]; then
        read -p "Enter new tag: " new_tag
        if [[ -n "$new_tag" ]]; then
            TAG="$new_tag"
            print_status "Tag updated to: $TAG"
        else
            print_warning "No tag entered, keeping current tag: $TAG"
        fi
    fi
}

# Function to build the app
build_app() {
    local tag=$1

    print_status "Building application"

    # Check if Dockerfile exists in root
    if [[ ! -f "Dockerfile" ]]; then
        print_error "Dockerfile not found in project root"
        return 1
    fi

    # Build the image
    local image_name="$REPO_NAME/$APP_NAME:$tag"
    print_status "Building image: $image_name"

    if docker build -t "$image_name" .; then
        print_success "Successfully built: $image_name"

        # Show image size
        local size=$(docker images "$image_name" --format "{{.Size}}")
        print_status "Image size: $size"
        return 0
    else
        print_error "Failed to build image: $image_name"
        return 1
    fi
}

# Function to push image to GHCR
push_image() {
    local tag=$1
    local local_image="$REPO_NAME/$APP_NAME:$tag"
    local remote_image="$REGISTRY/$GITHUB_USERNAME/$REPO_NAME/$APP_NAME:$tag"

    print_status "Preparing to push image to GHCR..."

    # Check if local image exists
    if ! docker image inspect "$local_image" >/dev/null 2>&1; then
        print_error "Local image '$local_image' not found. Build the image first."
        return 1
    fi

    # Check if user is logged into GHCR
    if ! docker info 2>/dev/null | grep -q "$REGISTRY"; then
        print_warning "Not logged into GHCR. You need to login first."
        echo "To push to GHCR, you need to:"
        echo "1. Create a GitHub Personal Access Token with 'write:packages' scope"
        echo "2. Login using: echo \$GITHUB_TOKEN | docker login $REGISTRY -u $GITHUB_USERNAME --password-stdin"
        read -p "Have you already logged in? (y/N): " logged_in
        if [[ ! "$logged_in" =~ ^[Yy]$ ]]; then
            print_error "Please login to GHCR first and try again"
            return 1
        fi
    fi

    # Tag the image for GHCR
    print_status "Tagging image for GHCR: $remote_image"
    if ! docker tag "$local_image" "$remote_image"; then
        print_error "Failed to tag image for GHCR"
        return 1
    fi

    # Push the image
    print_status "Pushing image to GHCR: $remote_image"
    if docker push "$remote_image"; then
        print_success "Successfully pushed: $remote_image"

        # Show the package URL
        print_status "Package URL: https://github.com/$GITHUB_USERNAME/packages/container/$REPO_NAME%2F$APP_NAME"
        return 0
    else
        print_error "Failed to push: $remote_image"
        return 1
    fi
}

# Main script
main() {
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running or not accessible"
        exit 1
    fi

    # Prompt user to change tag if desired
    prompt_tag_change

    print_status "Repository: $REPO_NAME"
    print_status "Tag: $TAG"
    if [[ "$PUSH_IMAGE" == true ]]; then
        print_status "Push to GHCR: enabled"
    fi
    echo ""

    # Build the app
    if ! build_app "$TAG"; then
        exit 1
    fi

    # Push to GHCR if requested
    if [[ "$PUSH_IMAGE" == true ]]; then
        if ! push_image "$TAG"; then
            exit 1
        fi
    fi

    # Option to run the container
    read -p "Do you want to run the container? (y/N): " run_container
    if [[ "$run_container" =~ ^[Yy]$ ]]; then
        print_status "Running container..."
        docker run --rm -p 8000:8000 "$REPO_NAME/$APP_NAME:$TAG"
    fi
}

# Run main function
main "$@"
