var owl = require('../../')
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