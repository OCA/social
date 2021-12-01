var events = require('events')
  , should = require('should')
  , owl = require('../')
  , Blog = owl.Blog;
  
describe('Blog', function() {
  
  describe('#constructor()', function() {
    
    it('extends events.EventEmitter', function() {
      var blog = new Blog;
      Blog.super_.should.equal(events.EventEmitter);
      blog.should.be.an.instanceof(events.EventEmitter);
    });
    
    it('sets default settings', function() {
      var blog = new Blog;
      blog.options.should.exist;
      blog.options.mongo.should.equal('mongodb://localhost/blog');
      blog.options.posts.should.equal('./posts');
      blog.options.pages.should.equal('./pages');
      blog.options.debug.should.be.false;
    });
    
    it('overrides default settings', function() {
      var blog = new Blog({
          mongo: 'mongodb://localhost/test'
        , posts: './test/posts'
        , pages: './test/pages'
        , debug: true
      });
      blog.options.mongo.should.equal('mongodb://localhost/test');
      blog.options.posts.should.equal('./test/posts');
      blog.options.pages.should.equal('./test/pages');
      blog.options.debug.should.be.true;
    });
    
    it('creates a mongodb connection with mongoose', function() {
      var blog = new Blog;
      blog.db.should.exist;
      blog.db.models.should.exist;
      blog.db.models.Post.should.exist;
    });
    
  });
  
  describe('#set()', function() {
    
    var blog = new Blog;
    
    it('returns the value of an option if no value', function() {
      blog.set('mongo').should.equal(blog.options.mongo);
      blog.set('debug').should.equal(blog.options.debug);
    });
    
    it('overrides an already-set value', function() {
      var old = blog.set('mongo');
      old.should.exist;
      blog.set('mongo', 'mongodb://localhost/test');
      blog.options.mongo.should.not.equal(old);
    });
    
    it('doesn\'t fail if the key doesn\'t exist', function() {
      should.not.exist(blog.set('test'));
    });
    
    it('sets an option that doesn\'t exist', function() {
      should.not.exist(blog.options.key);
      blog.set('key', 'value');
      blog.options.key.should.exist;
      blog.set('key').should.equal(blog.options.key);
    });
    
  });
  
  describe('#init()', function() {
    
    var blog;
    beforeEach(function() {
      blog = new Blog({
          mongo: 'mongodb://localhost/test'
        , posts: __dirname + '/posts'
        , pages: __dirname + '/pages'
      });
    });
    
    afterEach(function() {
      blog.Post.find().remove();
    });
    
    it('creates post and page watchers', function(done) {
      blog.init(function(e) {
        should.not.exist(e);
        blog.postWatcher.should.exist;
        blog.pageWatcher.should.exist;
        done();
      });
    });
    
    it('emits the "init" event', function(done) {
      blog.on('init', function(e) {
        should.not.exist(e);
        done();
      });
      blog.init();
    });
    
    it('updates/creates posts and pages', function(done) {
      blog.init(function(e) {
        should.not.exist(e);
        done();
      });
    });
    
  });
  
});