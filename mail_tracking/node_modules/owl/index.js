exports.Blog = require('./lib/blog');

exports.createBlog = function(options) {
  return new exports.Blog(options);
};
