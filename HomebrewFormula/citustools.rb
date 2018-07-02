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
  url "https://github.com/citusdata/tools/archive/v0.7.7.tar.gz"
  sha256 "5d3c29fb67575101c8b91c9bb4323d767646dae9f1a7fdc3d3a8871ff8401d81"

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
