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
  url "https://github.com/citusdata/tools/archive/v0.7.3.tar.gz"
  sha256 "664a388d7bfb07c86d9de935823642795ca125912dd970891e36fad8befeb60e"

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
