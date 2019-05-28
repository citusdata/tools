class Docker < Requirement
  fatal true

  satisfy { which "docker" }

  def message
    "Docker is required. Get it at https://www.docker.com/docker-mac"
  end
end

class Citustools < Formula
  desc "Tools and config used in Citus Data projects."
  homepage "https://github.com/citusdata/tools"
  url "https://github.com/citusdata/tools/archive/v0.7.10.tar.gz"
  sha256 "b16973b32c89be699e3f7924bc3afe04fe5d3c86407632d51b9e6ccf75a38f16"

  depends_on "uncrustify"
  depends_on Docker

  def install
    # FIXME: ensure installdirs runs exactly once
    ENV.deparallelize

    system "make", "install", "prefix=#{prefix}", "sysconfdir=#{etc}"
  end

  test do
    system "true"
  end
end
