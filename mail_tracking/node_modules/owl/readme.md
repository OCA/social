![OWL](https://raw.github.com/cpetzold/owl/master/etc/logo.gif)

**OWL** (**O**WL **W**atches **L**etters) is a simple node.js blogging engine backed by MongoDB and the file system. It was heavily influenced by [reed](https://github.com/ProjectMoon/reed).

## Summary

With owl, writing a blog post or static page means creating a new markdown file in either the posts or pages directory. If owl is running when the new file is saved, it will read the file, parse the markdown, apply the meta data set in the file, and save the post/page to mongo. Any modifications to this file will trigger the same cycle, ultimately updating the post on the database.  If owl isn't running, it will pick up the changes later on initialization.

In order to define a title, tags, or other metadata associated with a post or page, key/value definitions at the top of the file are required.  Look at the examples or read further to see the format.

If a file is removed, the corresponding database entry will also be removed.  This, along with most other aspects of owl, is configurable.  Look at the documentation on *createBlog* for all possible options.

## Documentation

### owl.createBlog([ options ])

Returns a Blog instance, defaulting to the following options.

```javascript
var owl = require('owl');

var blog = owl.createBlog({
    posts: './posts' // Post directory
  , pages: './pages' // Page directory
  , mongo: 'mongodb://localhost/blog' // MongoDB URI
  , debug: false
});
```

### blog.set(key[, value ])

Sets (if passed a value) or gets an internal or arbitrary setting.

```javascript
blog.set('posts'); // => './posts'
blog.set('posts', __dirname + '/content');
```

### blog.init([ callback ])

Initializes the post/page directory watchers and performs an update on both.  On completion, the optional `callback` is called and the `init` event fired.

```javascript
blog.init(function(e) {
  ...
});

blog.on('init', function(e) {
  ...
});
```

### blog.update(directory[, callback ])

Looks through all files in the type of content specified (`posts` or `pages`), upserting the content corresponding to the file.

Emits either a `posts.updated` or `pages.updated` event.

```javascript
blog.update('posts', function(e) {
  ...
});

blog.on('posts.updated', function() {
  ...
});
```

### blog.posts(options|callback[, callback ])

Retrieves an array of posts, defaulting to the following options.

```javascript
blog.posts({
    page: 1
  , per_page: 10 // Set to 0 for no pagination
  , sort_path: 'date' // Path on which to sort, can be nested (ex: 'meta.title')
  , sort_dir: 'desc' // Sort direction ('desc' or 'asc')
}, function(e, posts) {
  ...
});
```

### blog.post(slug, callback)

Retrieves a post. The `slug` is, by default, the filename excluding '.md'

```javascript
blog.post('hello-world', function(e, post) {
  ...
});
```

### blog.page(slug, callback)

Retrieves a page. The `slug` is, by default, the filename excluding '.md'

```javascript
blog.page('about', function(e, page) {
  ...
});
```

## Example

The following is the inlined contents of `examples/simple`

### blog.js

```javascript
var owl = require('owl')
  , blog = owl.createBlog({ posts: './posts', pages: './pages' });
  
blog.init(function(e) {
    
  blog.post('example-post', function(e, post) {
    console.log(post);
    /** 
     *  {   title: 'Example Post'
     *    , slug: 'example-post'
     *    , date: Date(Sat, 04 Feb 2012 08:00:00 GMT)
     *    , md: '## This is a *simple* owl blog post\n...'
     *    , html: '<h2>This is a <em>simple</em> owl blog post</h2>\n...'
     *    , comments: [ ]
     *    , ... }
     **/
  });
  
  blog.posts(function(e, posts) {
    console.log(posts);
    /** 
     * [ {   title: 'Example Post'
     *     , slug: 'example-post'
     *     , ... } ]
     */
  });
  
  blog.page('example-page', function(e, page) {
    console.log(page);
    /** 
     *  {   title: 'Example Page'
     *    , slug: 'example-page'
     *    , md: '### This is example page\n...', 
     *    , ... }
     **/
  });

});
```

### posts/example-post.md

    title: Example Post
    date: 2-4-2012
    tags: example, test, owl, blog

    ## This is a *simple* owl blog post

    This is [github-flavored markdown](http://github.github.com/github-flavored-markdown/):

    words_inside_here_won't_be_italicized

    ```javascript
    var foo = 'bar!';
    ```

### pages/example-page.md

    title: Example page

    ### This is a example page!


## Features

  * Watches **post** and **page** markdown (.md) in the specified directories and syncs them with mongo documents.
  
  * Supports title, date, tags, and other metadata
  
  * Provides a simple commenting system with markdown support.
  
  * API is both callback and event driven.
  
  * All markdown is [github flavored](http://github.github.com/github-flavored-markdown/)
  
## Test

In the root:

    npm install -g mocha
    mocha


## License

(The MIT License)

Copyright (c) 2012 Conner Petzold <cpetzold@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the 'Software'), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.